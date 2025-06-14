#!/bin/bash

# Human Lens API Deployment Script for DigitalOcean
# This script deploys the application without Docker containers

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="human-lens-api"
APP_USER="hlapi"
APP_DIR="/opt/human-lens-api"
REPO_URL="https://github.com/your-username/human-lens-api.git"  # Replace with actual repo
PYTHON_VERSION="python3.12"
SERVICE_NAME="human-lens-api"
NGINX_CONF="/etc/nginx/sites-available/${APP_NAME}"
DOMAIN="your-domain.com"  # Replace with actual domain

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

install_system_dependencies() {
    log_info "Installing system dependencies..."
    
    apt-get update
    apt-get install -y \
        python3.12 \
        python3.12-venv \
        python3.12-dev \
        python3-pip \
        git \
        nginx \
        supervisor \
        build-essential \
        libpq-dev \
        curl \
        htop \
        unzip \
        certbot \
        python3-certbot-nginx
    
    log_success "System dependencies installed"
}

create_app_user() {
    log_info "Creating application user..."
    
    if ! id "$APP_USER" &>/dev/null; then
        useradd --system --home-dir $APP_DIR --shell /bin/bash $APP_USER
        log_success "User $APP_USER created"
    else
        log_warning "User $APP_USER already exists"
    fi
}

setup_directories() {
    log_info "Setting up directories..."
    
    mkdir -p $APP_DIR
    mkdir -p $APP_DIR/data
    mkdir -p $APP_DIR/logs
    mkdir -p $APP_DIR/backups
    mkdir -p $APP_DIR/static
    mkdir -p /var/log/$APP_NAME
    
    chown -R $APP_USER:$APP_USER $APP_DIR
    chown -R $APP_USER:$APP_USER /var/log/$APP_NAME
    
    log_success "Directories created"
}

clone_or_update_repo() {
    log_info "Cloning/updating repository..."
    
    if [ -d "$APP_DIR/.git" ]; then
        log_info "Repository exists, pulling latest changes..."
        cd $APP_DIR
        sudo -u $APP_USER git fetch --all
        sudo -u $APP_USER git reset --hard origin/main
        sudo -u $APP_USER git pull origin main
    else
        log_info "Cloning repository..."
        cd /opt
        sudo -u $APP_USER git clone $REPO_URL $APP_DIR
        cd $APP_DIR
    fi
    
    log_success "Repository updated"
}

setup_python_environment() {
    log_info "Setting up Python environment..."
    
    cd $APP_DIR
    
    # Remove old venv if exists
    if [ -d "venv" ]; then
        rm -rf venv
    fi
    
    # Create new virtual environment
    sudo -u $APP_USER $PYTHON_VERSION -m venv venv
    
    # Upgrade pip and install dependencies
    sudo -u $APP_USER ./venv/bin/pip install --upgrade pip
    sudo -u $APP_USER ./venv/bin/pip install -r requirements.txt
    
    log_success "Python environment setup complete"
}

setup_environment_file() {
    log_info "Setting up environment file..."
    
    if [ ! -f "$APP_DIR/.env" ]; then
        log_warning ".env file not found, creating from template..."
        sudo -u $APP_USER cp $APP_DIR/.env.example $APP_DIR/.env
        
        # Generate secret key
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        sed -i "s/your-super-secret-key-change-this-in-production/$SECRET_KEY/" $APP_DIR/.env
        
        log_warning "Please edit $APP_DIR/.env with your actual configuration!"
        log_warning "Don't forget to set:"
        echo "  - SENDGRID_API_KEY"
        echo "  - STRIPE_PUBLISHABLE_KEY"
        echo "  - STRIPE_SECRET_KEY"
        echo "  - STRIPE_WEBHOOK_SECRET"
        echo "  - OPENAI_API_KEY"
        echo "  - ALLOWED_ORIGINS"
        
        read -p "Press Enter to continue after editing .env file..."
    else
        log_success ".env file already exists"
    fi
}

run_database_migrations() {
    log_info "Running database migrations..."
    
    cd $APP_DIR
    sudo -u $APP_USER ./venv/bin/python -c "from app.database import create_db_and_tables; create_db_and_tables()"
    
    log_success "Database migrations completed"
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Human Lens API
After=network.target

[Service]
Type=exec
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$APP_DIR /var/log/$APP_NAME
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    log_success "Systemd service created"
}

setup_nginx() {
    log_info "Setting up Nginx..."
    
    # Remove default nginx site
    rm -f /etc/nginx/sites-enabled/default
    
    # Create nginx configuration
    cat > $NGINX_CONF << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Serve static files
    location /static/ {
        alias $APP_DIR/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Frontend files
    location /app/ {
        alias $APP_DIR/frontend/;
        try_files \$uri \$uri/ /app/index.html;
        expires 1h;
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 8k;
        proxy_buffers 8 8k;
    }
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        access_log off;
    }
    
    # Root location
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Deny access to sensitive files
    location ~ /\.env {
        deny all;
        return 404;
    }
    
    location ~ /\.git {
        deny all;
        return 404;
    }
}
EOF

    # Enable site
    ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
    
    # Test nginx configuration
    nginx -t
    
    # Reload nginx
    systemctl reload nginx
    
    log_success "Nginx configured"
}

setup_ssl() {
    log_info "Setting up SSL certificate..."
    
    # Only run if domain is not localhost or IP
    if [[ "$DOMAIN" != "localhost" && "$DOMAIN" != *"."*"."*"."* ]]; then
        certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
        log_success "SSL certificate installed"
    else
        log_warning "Skipping SSL setup for local/IP domain"
    fi
}

setup_firewall() {
    log_info "Setting up firewall..."
    
    # Install ufw if not present
    apt-get install -y ufw
    
    # Reset firewall
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (be careful!)
    ufw allow ssh
    
    # Allow HTTP and HTTPS
    ufw allow 'Nginx Full'
    
    # Enable firewall
    ufw --force enable
    
    log_success "Firewall configured"
}

setup_monitoring() {
    log_info "Setting up basic monitoring..."
    
    # Create log rotation
    cat > /etc/logrotate.d/$APP_NAME << EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $APP_USER $APP_USER
    postrotate
        systemctl reload $SERVICE_NAME
    endscript
}
EOF

    # Create backup script
    cat > /usr/local/bin/backup-human-lens << EOF
#!/bin/bash
BACKUP_DIR="$APP_DIR/backups"
DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="\$BACKUP_DIR/human_lens_\$DATE.db"

# Create backup
cp $APP_DIR/data/human_lens.db \$BACKUP_FILE

# Compress backup
gzip \$BACKUP_FILE

# Keep only last 7 days of backups
find \$BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: \$BACKUP_FILE.gz"
EOF

    chmod +x /usr/local/bin/backup-human-lens
    
    # Add cron job for daily backups
    echo "0 2 * * * root /usr/local/bin/backup-human-lens" > /etc/cron.d/human-lens-backup
    
    log_success "Monitoring and backups configured"
}

create_admin_user() {
    log_info "Creating admin user..."
    
    cd $APP_DIR
    
    # Create superadmin user script
    cat > create_admin.py << 'EOF'
import asyncio
from app.database import get_session
from app.models import User, Organization, UserRole
from app.auth import get_password_hash

async def create_admin():
    session = next(get_session())
    
    # Check if admin exists
    admin = session.query(User).filter_by(email="admin@kookooha.com").first()
    if admin:
        print("Admin user already exists")
        return
    
    # Create admin organization
    org = Organization(name="Kookooha Admin", description="Administrative organization")
    session.add(org)
    session.commit()
    session.refresh(org)
    
    # Create admin user
    admin_user = User(
        email="admin@kookooha.com",
        first_name="Admin",
        last_name="User",
        role=UserRole.SUPERADMIN,
        org_id=org.id,
        hashed_password=get_password_hash("change_this_password_123!"),
        is_active=True,
        is_verified=True
    )
    
    session.add(admin_user)
    session.commit()
    
    print(f"Admin user created: admin@kookooha.com")
    print("Password: change_this_password_123!")
    print("Please change this password immediately!")

if __name__ == "__main__":
    asyncio.run(create_admin())
EOF

    sudo -u $APP_USER ./venv/bin/python create_admin.py
    rm create_admin.py
    
    log_success "Admin user created"
}

restart_services() {
    log_info "Restarting services..."
    
    # Restart application
    systemctl restart $SERVICE_NAME
    
    # Restart nginx
    systemctl restart nginx
    
    # Wait a moment
    sleep 3
    
    # Check service status
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_success "Application service is running"
    else
        log_error "Application service failed to start"
        systemctl status $SERVICE_NAME
        exit 1
    fi
    
    if systemctl is-active --quiet nginx; then
        log_success "Nginx is running"
    else
        log_error "Nginx failed to start"
        systemctl status nginx
        exit 1
    fi
}

run_health_check() {
    log_info "Running health check..."
    
    # Wait for application to start
    sleep 5
    
    # Test health endpoint
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        log_info "Checking application logs..."
        journalctl -u $SERVICE_NAME --no-pager -n 20
        exit 1
    fi
}

print_deployment_info() {
    log_success "Deployment completed successfully!"
    echo ""
    echo -e "${BLUE}Application Information:${NC}"
    echo "  - Application URL: http://$DOMAIN"
    echo "  - API Documentation: http://$DOMAIN/docs"
    echo "  - Health Check: http://$DOMAIN/health"
    echo "  - Admin Email: admin@kookooha.com"
    echo "  - Admin Password: change_this_password_123!"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  - View logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "  - Restart app: sudo systemctl restart $SERVICE_NAME"
    echo "  - Check status: sudo systemctl status $SERVICE_NAME"
    echo "  - View nginx logs: sudo tail -f /var/log/nginx/error.log"
    echo "  - Create backup: sudo /usr/local/bin/backup-human-lens"
    echo ""
    echo -e "${YELLOW}Important:${NC}"
    echo "  1. Change the admin password immediately!"
    echo "  2. Update .env file with your actual API keys"
    echo "  3. Configure your domain DNS to point to this server"
    echo "  4. Set up SSL certificate if using a real domain"
    echo ""
}

# Main deployment function
main() {
    log_info "Starting Human Lens API deployment..."
    
    check_root
    install_system_dependencies
    create_app_user
    setup_directories
    clone_or_update_repo
    setup_python_environment
    setup_environment_file
    run_database_migrations
    create_systemd_service
    setup_nginx
    setup_firewall
    setup_monitoring
    create_admin_user
    restart_services
    run_health_check
    
    # Only setup SSL for real domains
    if [[ "$DOMAIN" != "localhost" && "$DOMAIN" =~ \. ]]; then
        setup_ssl
    fi
    
    print_deployment_info
}

# Handle script arguments
case "${1:-}" in
    --update-only)
        log_info "Running update-only deployment..."
        clone_or_update_repo
        setup_python_environment
        run_database_migrations
        restart_services
        run_health_check
        log_success "Update completed!"
        ;;
    --ssl-only)
        log_info "Setting up SSL only..."
        setup_ssl
        ;;
    --help)
        echo "Human Lens API Deployment Script"
        echo ""
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  (no option)   Full deployment"
        echo "  --update-only Update code and restart services"
        echo "  --ssl-only    Setup SSL certificate only"
        echo "  --help        Show this help"
        echo ""
        echo "Before running, edit the configuration variables at the top of this script:"
        echo "  - REPO_URL: Your git repository URL"
        echo "  - DOMAIN: Your domain name"
        ;;
    *)
        main
        ;;
esac
