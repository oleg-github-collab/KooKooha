"""Authentication and authorization utilities."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from .config import settings
from .database import get_session
from .models import User, UserRole, SurveyInvitation


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token security
security = HTTPBearer()


class AuthException(HTTPException):
    """Custom authentication exception."""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_survey_token(survey_id: int, respondent_id: Optional[int] = None, 
                       invitation_id: Optional[int] = None) -> str:
    """Create a survey invitation token."""
    to_encode = {
        "survey_id": survey_id,
        "respondent_id": respondent_id,
        "invitation_id": invitation_id,
        "type": "survey",
        "exp": datetime.utcnow() + timedelta(days=settings.survey_token_expire_days)
    }
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        token_type = payload.get("type")
        
        if token_type != expected_type:
            raise AuthException(f"Invalid token type. Expected {expected_type}")
        
        return payload
    except JWTError as e:
        raise AuthException(f"Token validation failed: {str(e)}")


def generate_random_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    user_id = payload.get("sub")
    if user_id is None:
        raise AuthException("Token missing user ID")
    
    statement = select(User).where(User.id == int(user_id), User.is_active == True)
    user = session.exec(statement).first()
    
    if user is None:
        raise AuthException("User not found")
    
    # Update last login
    user.last_login = datetime.utcnow()
    session.add(user)
    session.commit()
    
    return user


async def get_current_superadmin(current_user: User = Depends(get_current_user)) -> User:
    """Get current user and verify superadmin role."""
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. SuperAdmin role required."
        )
    return current_user


async def get_current_client_admin(current_user: User = Depends(get_current_user)) -> User:
    """Get current user and verify client admin role."""
    if current_user.role not in [UserRole.CLIENTADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. ClientAdmin role required."
        )
    return current_user


async def verify_organization_access(
    org_id: int,
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify user has access to organization."""
    if current_user.role == UserRole.SUPERADMIN:
        return current_user
    
    if current_user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    return current_user


async def verify_survey_token(
    token: str,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Verify survey invitation token and return survey details."""
    try:
        payload = verify_token(token, "survey")
        survey_id = payload.get("survey_id")
        invitation_id = payload.get("invitation_id")
        
        if not survey_id:
            raise AuthException("Invalid survey token")
        
        # If invitation_id is provided, verify the invitation exists and is valid
        if invitation_id:
            statement = select(SurveyInvitation).where(
                SurveyInvitation.id == invitation_id,
                SurveyInvitation.survey_id == survey_id,
                SurveyInvitation.expires_at > datetime.utcnow()
            )
            invitation = session.exec(statement).first()
            
            if not invitation:
                raise AuthException("Invalid or expired invitation")
            
            # Mark invitation as opened if not already
            if not invitation.opened_at:
                invitation.opened_at = datetime.utcnow()
                session.add(invitation)
                session.commit()
        
        return payload
        
    except JWTError as e:
        raise AuthException(f"Invalid survey token: {str(e)}")


def authenticate_user(email: str, password: str, session: Session) -> Optional[User]:
    """Authenticate user with email and password."""
    statement = select(User).where(User.email == email, User.is_active == True)
    user = session.exec(statement).first()
    
    if not user:
        return None
    
    if not user.hashed_password:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


class RoleChecker:
    """Role-based access control."""
    
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[role.value for role in self.allowed_roles]}"
            )
        return current_user


# Convenience role checkers
require_superadmin = RoleChecker([UserRole.SUPERADMIN])
require_client_admin = RoleChecker([UserRole.CLIENTADMIN, UserRole.SUPERADMIN])
require_any_admin = RoleChecker([UserRole.CLIENTADMIN, UserRole.SUPERADMIN])
