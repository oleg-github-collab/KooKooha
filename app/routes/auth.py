"""Authentication routes."""
from datetime import timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr
import structlog

from ..database import get_session
from ..models import User, UserCreate, UserRead, Organization, OrganizationCreate, UserRole
from ..auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_token,
    get_current_user,
)
from ..config import settings


logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()


class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class RegisterRequest(BaseModel):
    """Registration request model."""
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    organization_name: str
    organization_description: str = ""
    organization_website: str = ""
    organization_industry: str = ""


class RegisterResponse(BaseModel):
    """Registration response model."""
    message: str
    user: UserRead
    organization_id: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request model."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model."""
    token: str
    new_password: str


@router.post("/register", response_model=RegisterResponse)
async def register(
    register_data: RegisterRequest,
    session: Session = Depends(get_session)
):
    """Register a new client admin and create organization."""
    logger.info("Registration attempt", email=register_data.email)
    
    # Check if user already exists
    statement = select(User).where(User.email == register_data.email)
    existing_user = session.exec(statement).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    try:
        # Create organization
        org_data = OrganizationCreate(
            name=register_data.organization_name,
            description=register_data.organization_description,
            website=register_data.organization_website,
            industry=register_data.organization_industry,
        )
        organization = Organization.model_validate(org_data)
        session.add(organization)
        session.commit()
        session.refresh(organization)
        
        # Create user
        user_data = UserCreate(
            email=register_data.email,
            password=register_data.password,
            first_name=register_data.first_name,
            last_name=register_data.last_name,
            role=UserRole.CLIENTADMIN,
            org_id=organization.id,
        )
        
        user = User(
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
            org_id=organization.id,
            hashed_password=get_password_hash(user_data.password),
            is_active=True,
            is_verified=True,  # Auto-verify for client admins
        )
        
        session.add(user)
        session.commit()
        session.refresh(user)
        
        logger.info(
            "User registered successfully",
            user_id=user.id,
            email=user.email,
            org_id=organization.id,
        )
        
        return RegisterResponse(
            message="Registration successful",
            user=UserRead.model_validate(user),
            organization_id=organization.id,
        )
        
    except Exception as e:
        session.rollback()
        logger.error("Registration failed", error=str(e), email=register_data.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    session: Session = Depends(get_session)
):
    """Authenticate user and return tokens."""
    logger.info("Login attempt", email=login_data.email)
    
    user = authenticate_user(login_data.email, login_data.password, session)
    
    if not user:
        logger.warning("Login failed - invalid credentials", email=login_data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning("Login failed - inactive user", email=login_data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    logger.info("Login successful", user_id=user.id, email=user.email)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserRead.model_validate(user),
    )


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    session: Session = Depends(get_session)
):
    """Refresh access token using refresh token."""
    try:
        payload = verify_token(refresh_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user and verify they're still active
        statement = select(User).where(User.id == int(user_id), User.is_active == True)
        user = session.exec(statement).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role},
            expires_delta=access_token_expires
        )
        
        logger.info("Token refreshed", user_id=user.id)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }
        
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserRead.model_validate(current_user)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout current user."""
    # In a more sophisticated implementation, we might blacklist the token
    # For now, just log the action
    logger.info("User logged out", user_id=current_user.id)
    return {"message": "Successfully logged out"}


@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    session: Session = Depends(get_session)
):
    """Request password reset."""
    # Check if user exists
    statement = select(User).where(User.email == request.email, User.is_active == True)
    user = session.exec(statement).first()
    
    if not user:
        # Don't reveal if email exists or not
        logger.warning("Password reset requested for non-existent email", email=request.email)
        return {"message": "If the email exists, a reset link has been sent"}
    
    # In a real application we would send a password reset email here.
    # For now, just log the request
    logger.info("Password reset requested", user_id=user.id, email=user.email)
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    request: PasswordResetConfirm,
    session: Session = Depends(get_session)
):
    """Reset password using token."""
    try:
        # Verify reset token (implementation depends on how reset tokens are created)
        payload = verify_token(request.token, "password_reset")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        # Get user
        statement = select(User).where(User.id == int(user_id), User.is_active == True)
        user = session.exec(statement).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found"
            )
        
        # Update password
        user.hashed_password = get_password_hash(request.new_password)
        session.add(user)
        session.commit()
        
        logger.info("Password reset successful", user_id=user.id)
        
        return {"message": "Password reset successful"}
        
    except Exception as e:
        logger.error("Password reset failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
