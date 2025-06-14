# Human Lens API

**Advanced Sociometric & Team Analytics Platform**

Human Lens is a comprehensive API platform for conducting sociometric analysis, 360-degree reviews, eNPS surveys, and team dynamics assessments. Built with modern Python technologies and designed for scalability, privacy, and actionable insights.

Additional documentation is available in the `docs` directory:
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Environment Variables](docs/ENVIRONMENT.md)
- [API Overview](docs/ENDPOINTS.md)

## 🚀 Features

### Core Functionality
- **Multi-Type Surveys**: Sociometry, 360-reviews, eNPS, team dynamics
- **Real-time Analytics**: Network visualization, team cohesion scoring, communication analysis
- **AI-Powered Insights**: OpenAI integration for intelligent recommendations
- **Team Management**: CSV/Excel import, automated invitations, role-based access
- **Payment Processing**: Stripe integration with flexible pricing models
- **Email Automation**: SendGrid integration with beautiful templates

### Technical Features
- **Modern Python Stack**: FastAPI, SQLModel, Pydantic v2
- **Database**: SQLite with automated migrations
- **Authentication**: JWT with role-based access control
- **Scheduling**: APScheduler for automated tasks
- **Analytics**: NetworkX, pandas, scikit-learn for data processing
- **Monitoring**: Structured logging, health checks, system metrics

### Security & Privacy
- **Data Protection**: GDPR-compliant anonymization options
- **Secure Authentication**: BCrypt password hashing, JWT tokens
- **Rate Limiting**: Built-in API rate limiting
- **Input Validation**: Comprehensive data validation with Pydantic
- **Audit Logging**: Complete activity tracking

## 📋 Prerequisites

- **Python 3.12+**
- **Git**
- **SendGrid API Key** (for email)
- **Stripe Account** (for payments)
- **OpenAI API Key** (optional, for AI insights)

## 🛠 Installation

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/your-username/human-lens-api.git
cd human-lens-api
```

2. **Quick Start**
```bash
make quick-start
```

This will:
- Create virtual environment
- Install dependencies
- Copy environment template
- Run database migrations
- Run tests

3. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

4. **Start Development Server**
```bash
make run
```

The API will be available at `http://localhost:8000`

### Manual Installation

1. **Create Virtual Environment**
```bash
python3.12 -m venv venv
source venv/bin/activate
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Database Setup**
```bash
make migrate
```

4. **Run Application**
```bash
uvicorn app.main:app --reload
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Application
SECRET_KEY="your-secret-key"
DEBUG=false
ENVIRONMENT="production"

# Database
DATABASE_URL="sqlite:///./data/human_lens.db"

# SendGrid Email
SENDGRID_API_KEY="your-sendgrid-api-key"
FROM_EMAIL="noreply@yourdomain.com"
FROM_NAME="Your Company"

# Stripe Payments
STRIPE_PUBLISHABLE_KEY="pk_live_your_key"
STRIPE_SECRET_KEY="sk_live_your_key"
STRIPE_WEBHOOK_SECRET="whsec_your_webhook_secret"

# OpenAI (Optional)
OPENAI_API_KEY="your-openai-api-key"

# CORS
ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"

# Frontend URLs
FRONTEND_URL="https://yourdomain.com"
SURVEY_URL_TEMPLATE="https://yourdomain.com/survey/{token}"
```

### Pricing Configuration

```bash
# Base package (4 people, 2 criteria) = €750
BASE_PRICE_CENTS=75000
BASE_TEAM_SIZE=4
BASE_CRITERIA_COUNT=2

# Additional costs
PRICE_PER_ADDITIONAL_PERSON_CENTS=7500  # €75 per person
PRICE_PER_ADDITIONAL_CRITERIA_CENTS=15000  # €150 per criteria
```

## 🚀 Production Deployment

### DigitalOcean Deployment

1. **Prepare Deployment Script**
```bash
# Edit deploy.sh configuration
REPO_URL="https://github.com/your-username/human-lens-api.git"
DOMAIN="your-domain.com"
```

2. **Run Deployment**
```bash
chmod +x deploy.sh
sudo ./deploy.sh
```

The deployment script will:
- Install system dependencies
- Create application user
- Set up Python environment
- Configure Nginx reverse proxy
- Set up SSL certificates
- Create systemd service
- Configure firewall
- Set up monitoring and backups

### Manual Production Setup

1. **Install Dependencies**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv nginx supervisor git
```

2. **Create Application User**
```bash
sudo useradd --system --home-dir /opt/human-lens-api hlapi
```

3. **Deploy Application**
```bash
sudo -u hlapi git clone https://github.com/your-username/human-lens-api.git /opt/human-lens-api
cd /opt/human-lens-api
sudo -u hlapi python3.12 -m venv venv
sudo -u hlapi ./venv/bin/pip install -r requirements.txt
```

4. **Configure Systemd Service**
```bash
sudo cp deploy/human-lens-api.service /etc/systemd/system/
sudo systemctl enable human-lens-api
sudo systemctl start human-lens-api
```

## 📊 API Usage

### Authentication

1. **Register Organization**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@company.com",
    "password": "securepassword123",
    "first_name": "John",
    "last_name": "Doe",
    "organization_name": "Acme Corp",
    "organization_description": "Leading technology company"
  }'
```

2. **Login**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@company.com",
    "password": "securepassword123"
  }'
```

3. **Use JWT Token**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/me"
```

### Team Management

1. **Import Team Members**
```bash
curl -X POST "http://localhost:8000/api/v1/organizations/1/team/import" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "members": [
      {
        "email": "employee1@company.com",
        "first_name": "Alice",
        "last_name": "Smith",
        "department": "Engineering"
      }
    ],
    "send_invitations": true
  }'
```

### Survey Management

1. **Create Survey**
```bash
curl -X POST "http://localhost:8000/api/v1/surveys?org_id=1" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Team Dynamics Assessment",
    "description": "Quarterly team assessment",
    "survey_type": "sociometry",
    "anonymize_responses": true
  }'
```

2. **Activate Survey**
```bash
curl -X POST "http://localhost:8000/api/v1/surveys/1/activate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "send_invitations": true
  }'
```

### Analytics

1. **Get Survey Dashboard**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/analytics/dashboard/1"
```

2. **Get Network Visualization**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/analytics/network/1"
```

## 🧪 Testing

### Run Tests
```bash
# All tests with coverage
make test

# Quick tests
make test-quick

# Specific test file
pytest tests/test_auth.py -v

# With coverage report
pytest --cov=app --cov-report=html
```

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing
- **Performance Tests**: Load and stress testing

## 📈 Monitoring

### Health Checks
```bash
# Application health
curl http://localhost:8000/health

# Detailed system health (admin only)
curl -H "Authorization: Bearer ADMIN_TOKEN" \
  http://localhost:8000/api/v1/admin/system/health
```

### Logs
```bash
# Application logs
tail -f logs/app.log

# System service logs
sudo journalctl -u human-lens-api -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Metrics
- Response times and error rates
- Database query performance
- Memory and CPU usage
- Email delivery rates
- Payment success rates

## 🔨 Development

### Available Commands
```bash
make help              # Show all available commands
make dev               # Full development setup
make run               # Start development server
make test              # Run tests
make lint              # Run linting
make format            # Format code
make clean             # Clean temporary files
```

### Code Structure
```
app/
├── main.py           # FastAPI application
├── config.py         # Configuration settings
├── database.py       # Database setup
├── models.py         # SQLModel models
├── auth.py           # Authentication utilities
├── routes/           # API route handlers
├── services/         # Business logic services
└── scripts/          # Utility scripts

tests/
├── unit/             # Unit tests
├── integration/      # Integration tests
└── e2e/              # End-to-end tests
```

### Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Write tests** for your changes
4. **Ensure tests pass**: `make test`
5. **Format code**: `make format`
6. **Commit changes**: `git commit -m 'Add amazing feature'`
7. **Push to branch**: `git push origin feature/amazing-feature`
8. **Open Pull Request**

## 🔐 Security

### Best Practices Implemented
- **Input Validation**: All inputs validated with Pydantic
- **SQL Injection Prevention**: Using SQLModel ORM
- **XSS Protection**: Proper content type headers
- **CSRF Protection**: SameSite cookie settings
- **Rate Limiting**: API rate limiting implemented
- **Secure Headers**: Security headers in responses
- **Password Security**: BCrypt hashing with salt

### Security Configuration
```bash
# Strong secret key
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Secure CORS settings
ALLOWED_ORIGINS="https://yourdomain.com"

# Rate limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
```

## 📝 API Documentation

### Interactive Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new organization |
| POST | `/api/v1/auth/login` | Authenticate user |
| GET | `/api/v1/me` | Get current user info |
| POST | `/api/v1/organizations/{id}/team/import` | Import team members |
| POST | `/api/v1/surveys` | Create new survey |
| POST | `/api/v1/surveys/{id}/activate` | Activate survey |
| GET | `/api/v1/analytics/dashboard/{id}` | Get survey analytics |
| POST | `/api/v1/payments/checkout` | Create payment session |

## 🗄️ Database

### Models
- **Users**: Authentication and user management
- **Organizations**: Company/team containers
- **Surveys**: Survey definitions and configuration
- **Responses**: Survey response data
- **Payments**: Payment tracking
- **Analytics**: Cached analytics data

### Migrations
```bash
# Run migrations
make migrate

# Reset database (development only)
rm data/human_lens.db && make migrate
```

## 💳 Payments

### Stripe Integration
1. **Create Stripe Account**
2. **Get API Keys** from Stripe Dashboard
3. **Configure Webhook** endpoint: `/api/v1/payments/webhook`
4. **Set Webhook Secret** in environment

### Pricing Model
- **Base Package**: €750 (4 people, 2 criteria)
- **Additional Person**: €75
- **Additional Criteria**: €150

Example calculation:
- 10 people, 5 criteria
- Base: €750 (4 people, 2 criteria)
- Additional people: 6 × €75 = €450
- Additional criteria: 3 × €150 = €450
- **Total: €1,650**

## 📧 Email System

### SendGrid Setup
1. **Create SendGrid Account**
2. **Create API Key** with Mail Send permissions
3. **Verify Sender Identity**
4. **Configure Domain Authentication** (recommended)

### Email Templates
- **Welcome Email**: New team member onboarding
- **Survey Invitation**: Survey participation request
- **Survey Reminder**: Follow-up reminders
- **Payment Confirmation**: Purchase receipts

## 🤖 AI Integration

### OpenAI Features
- **Survey Analysis**: Automated insights generation
- **Trend Analysis**: Pattern recognition in team data
- **Recommendations**: Actionable improvement suggestions
- **Report Generation**: Natural language summaries

### Configuration
```bash
OPENAI_API_KEY="your-openai-api-key"
OPENAI_MODEL="gpt-4"
```

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Error**
```bash
# Check database file permissions
ls -la data/human_lens.db
# Recreate database
rm data/human_lens.db && make migrate
```

2. **Email Not Sending**
```bash
# Check SendGrid API key
curl -X POST "https://api.sendgrid.com/v3/mail/send" \
  -H "Authorization: Bearer $SENDGRID_API_KEY" \
  -H "Content-Type: application/json"
```

3. **Payment Webhook Issues**
```bash
# Check Stripe webhook logs
# Verify webhook secret matches
# Test webhook endpoint
curl -X POST http://localhost:8000/api/v1/payments/webhook
```

4. **High Memory Usage**
```bash
# Check analytics cache
# Clean old snapshots
# Restart application
sudo systemctl restart human-lens-api
```

### Debug Mode
```bash
# Enable debug mode
export DEBUG=true
# Check detailed logs
tail -f logs/app.log | grep DEBUG
```

## 📞 Support

### Documentation
- **API Docs**: Available at `/docs` when running
- **Code Comments**: Inline documentation
- **Type Hints**: Full type annotation coverage

### Getting Help
1. **Check logs** for error details
2. **Review documentation** for configuration
3. **Search issues** in repository
4. **Create issue** with detailed description

### Performance Tuning
- **Database**: Add indexes for large datasets
- **Memory**: Adjust worker processes
- **Caching**: Enable analytics caching
- **CDN**: Use CDN for static files

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** for the excellent web framework
- **SQLModel** for the powerful ORM
- **Stripe** for payment processing
- **SendGrid** for email delivery
- **OpenAI** for AI capabilities
- **NetworkX** for graph analysis

---

**Human Lens API** - Transforming workplace analytics through technology

For more information, visit [https://kookooha.com](https://kookooha.com)
