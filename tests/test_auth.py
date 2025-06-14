"""Tests for authentication endpoints and functionality."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import User, UserRole, Organization
from app.auth import verify_password, get_password_hash, verify_token


@pytest.mark.auth
@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing functionality."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrongpassword", hashed)
    
    def test_different_passwords_produce_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2
    
    def test_same_password_produces_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "testpassword123"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


@pytest.mark.auth
@pytest.mark.unit
class TestTokenGeneration:
    """Test JWT token generation and verification."""
    
    def test_token_creation_and_verification(self):
        """Test JWT token creation and verification."""
        from app.auth import create_access_token
        
        data = {"sub": "123", "email": "test@example.com", "role": "clientadmin"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
        
        # Verify token
        payload = verify_token(token, "access")
        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "clientadmin"
        assert payload["type"] == "access"
        assert "exp" in payload
    
    def test_refresh_token_creation(self):
        """Test refresh token creation."""
        from app.auth import create_refresh_token
        
        data = {"sub": "123", "email": "test@example.com"}
        token = create_refresh_token(data)
        
        assert isinstance(token, str)
        
        # Verify it's a refresh token
        payload = verify_token(token, "refresh")
        assert payload["type"] == "refresh"
    
    def test_survey_token_creation(self):
        """Test survey invitation token creation."""
        from app.auth import create_survey_token
        
        token = create_survey_token(
            survey_id=1,
            respondent_id=123,
            invitation_id=456
        )
        
        assert isinstance(token, str)
        
        # This would normally be verified with session, but we test structure
        payload = verify_token(token, "survey")
        assert payload["survey_id"] == 1
        assert payload["respondent_id"] == 123
        assert payload["invitation_id"] == 456
        assert payload["type"] == "survey"
    
    def test_invalid_token_verification(self):
        """Test verification of invalid tokens."""
        from app.auth import AuthException
        
        with pytest.raises(AuthException):
            verify_token("invalid.token.here", "access")
        
        with pytest.raises(AuthException):
            verify_token("", "access")
    
    def test_wrong_token_type_verification(self):
        """Test verification with wrong token type."""
        from app.auth import create_access_token, AuthException
        
        data = {"sub": "123", "email": "test@example.com"}
        access_token = create_access_token(data)
        
        # Try to verify access token as refresh token
        with pytest.raises(AuthException):
            verify_token(access_token, "refresh")


@pytest.mark.auth
@pytest.mark.api
class TestAuthEndpoints:
    """Test authentication API endpoints."""
    
    def test_register_new_organization(self, client: TestClient):
        """Test registering a new organization and client admin."""
        register_data = {
            "email": "admin@newcompany.com",
            "password": "securepassword123",
            "first_name": "John",
            "last_name": "Doe",
            "organization_name": "New Company Inc",
            "organization_description": "A test company",
            "organization_website": "https://newcompany.com",
            "organization_industry": "Technology"
        }
        
        response = client.post("/api/v1/auth/register", json=register_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Registration successful"
        assert data["user"]["email"] == "admin@newcompany.com"
        assert data["user"]["role"] == "clientadmin"
        assert data["user"]["first_name"] == "John"
        assert data["user"]["last_name"] == "Doe"
        assert "organization_id" in data
    
    def test_register_duplicate_email(self, client: TestClient, test_client_admin: User):
        """Test registering with already existing email."""
        register_data = {
            "email": test_client_admin.email,
            "password": "password123",
            "first_name": "Test",
            "last_name": "User",
            "organization_name": "Test Company"
        }
        
        response = client.post("/api/v1/auth/register", json=register_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_register_invalid_data(self, client: TestClient):
        """Test registration with invalid data."""
        # Missing required fields
        register_data = {
            "email": "incomplete@test.com",
            "password": "short"  # Too short
        }
        
        response = client.post("/api/v1/auth/register", json=register_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_login_success(self, client: TestClient, test_client_admin: User):
        """Test successful login."""
        login_data = {
            "email": test_client_admin.email,
            "password": "testpassword123"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["user"]["email"] == test_client_admin.email
        assert data["user"]["role"] == test_client_admin.role
    
    def test_login_invalid_credentials(self, client: TestClient, test_client_admin: User):
        """Test login with invalid credentials."""
        login_data = {
            "email": test_client_admin.email,
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        login_data = {
            "email": "nonexistent@test.com",
            "password": "password123"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_inactive_user(self, client: TestClient, session: Session):
        """Test login with inactive user."""
        # Create inactive user
        inactive_user = User(
            email="inactive@test.com",
            first_name="Inactive",
            last_name="User",
            role=UserRole.CLIENTADMIN,
            hashed_password=get_password_hash("password123"),
            is_active=False  # Inactive
        )
        session.add(inactive_user)
        session.commit()
        
        login_data = {
            "email": "inactive@test.com",
            "password": "password123"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Account is inactive" in response.json()["detail"]
    
    def test_refresh_token_success(self, client: TestClient, test_client_admin: User):
        """Test successful token refresh."""
        from app.auth import create_refresh_token
        
        # Create refresh token
        refresh_token = create_refresh_token(
            data={"sub": str(test_client_admin.id), "email": test_client_admin.email}
        )
        
        refresh_data = {"refresh_token": refresh_token}
        
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_refresh_token_invalid(self, client: TestClient):
        """Test refresh with invalid token."""
        refresh_data = {"refresh_token": "invalid.token.here"}
        
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]
    
    def test_get_current_user(self, client: TestClient, auth_headers_client_admin: dict):
        """Test getting current user information."""
        response = client.get("/api/v1/auth/me", headers=auth_headers_client_admin)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == "admin@test.com"
        assert data["role"] == "clientadmin"
        assert "id" in data
        assert "created_at" in data
    
    def test_get_current_user_unauthorized(self, client: TestClient):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_logout(self, client: TestClient, auth_headers_client_admin: dict):
        """Test user logout."""
        response = client.post("/api/v1/auth/logout", headers=auth_headers_client_admin)
        
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]


@pytest.mark.auth
@pytest.mark.integration
class TestAuthIntegration:
    """Test authentication integration scenarios."""
    
    def test_complete_auth_flow(self, client: TestClient):
        """Test complete authentication flow from registration to logout."""
        # 1. Register
        register_data = {
            "email": "flowtest@test.com",
            "password": "testpassword123",
            "first_name": "Flow",
            "last_name": "Test",
            "organization_name": "Flow Test Company"
        }
        
        register_response = client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 200
        
        # 2. Login
        login_data = {
            "email": "flowtest@test.com",
            "password": "testpassword123"
        }
        
        login_response = client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # 3. Access protected endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "flowtest@test.com"
        
        # 4. Refresh token
        refresh_data = {"refresh_token": refresh_token}
        refresh_response = client.post("/api/v1/auth/refresh", json=refresh_data)
        assert refresh_response.status_code == 200
        
        new_access_token = refresh_response.json()["access_token"]
        assert new_access_token != access_token
        
        # 5. Use new token
        new_headers = {"Authorization": f"Bearer {new_access_token}"}
        me_response2 = client.get("/api/v1/auth/me", headers=new_headers)
        assert me_response2.status_code == 200
        
        # 6. Logout
        logout_response = client.post("/api/v1/auth/logout", headers=new_headers)
        assert logout_response.status_code == 200
    
    def test_role_based_access_control(self, client: TestClient, session: Session):
        """Test role-based access control."""
        from app.auth import get_password_hash
        
        # Create users with different roles
        org = Organization(name="RBAC Test Org")
        session.add(org)
        session.commit()
        session.refresh(org)
        
        superadmin = User(
            email="super@test.com",
            role=UserRole.SUPERADMIN,
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_verified=True
        )
        
        client_admin = User(
            email="client@test.com",
            role=UserRole.CLIENTADMIN,
            org_id=org.id,
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_verified=True
        )
        
        respondent = User(
            email="respondent@test.com",
            role=UserRole.RESPONDENT,
            org_id=org.id,
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_verified=True
        )
        
        session.add_all([superadmin, client_admin, respondent])
        session.commit()
        
        # Test access to admin endpoints
        from app.auth import create_access_token
        
        # SuperAdmin should have access
        super_token = create_access_token(
            data={"sub": str(superadmin.id), "email": superadmin.email, "role": superadmin.role}
        )
        super_headers = {"Authorization": f"Bearer {super_token}"}
        
        # ClientAdmin should have limited access
        client_token = create_access_token(
            data={"sub": str(client_admin.id), "email": client_admin.email, "role": client_admin.role}
        )
        client_headers = {"Authorization": f"Bearer {client_token}"}
        
        # Respondent should have minimal access
        respondent_token = create_access_token(
            data={"sub": str(respondent.id), "email": respondent.email, "role": respondent.role}
        )
        respondent_headers = {"Authorization": f"Bearer {respondent_token}"}
        
        # Test access to different endpoints
        # All should be able to access /me
        for headers in [super_headers, client_headers, respondent_headers]:
            response = client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code == 200
        
        # Only admins should access admin endpoints (when implemented)
        # This would be tested with actual admin endpoints
        