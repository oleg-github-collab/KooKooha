"""Database models using SQLModel."""
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import json

from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from pydantic import EmailStr, validator


class UserRole(str, Enum):
    """User roles enumeration."""
    SUPERADMIN = "superadmin"
    CLIENTADMIN = "clientadmin"
    RESPONDENT = "respondent"


class SurveyType(str, Enum):
    """Survey types enumeration."""
    SOCIOMETRY = "sociometry"
    REVIEW_360 = "360"
    ENPS = "enps"
    TEAM_DYNAMICS = "team_dynamics"


class SurveyStatus(str, Enum):
    """Survey status enumeration."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# Base models
class TimestampMixin(SQLModel):
    """Mixin for created_at and updated_at timestamps."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


# Organizations
class OrganizationBase(SQLModel):
    """Base organization model."""
    name: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    website: Optional[str] = Field(default=None, max_length=255)
    industry: Optional[str] = Field(default=None, max_length=100)


class Organization(OrganizationBase, TimestampMixin, table=True):
    """Organization database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    is_active: bool = Field(default=True)
    
    # Relationships
    users: List["User"] = Relationship(back_populates="organization")
    surveys: List["Survey"] = Relationship(back_populates="organization")
    payments: List["Payment"] = Relationship(back_populates="organization")


class OrganizationCreate(OrganizationBase):
    """Organization creation model."""
    pass


class OrganizationRead(OrganizationBase):
    """Organization read model."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]


class OrganizationUpdate(SQLModel):
    """Organization update model."""
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    website: Optional[str] = Field(default=None, max_length=255)
    industry: Optional[str] = Field(default=None, max_length=100)


# Users
class UserBase(SQLModel):
    """Base user model."""
    email: EmailStr
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    role: UserRole = Field(default=UserRole.RESPONDENT)


class User(UserBase, TimestampMixin, table=True):
    """User database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: Optional[int] = Field(default=None, foreign_key="organization.id")
    hashed_password: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    last_login: Optional[datetime] = Field(default=None)
    
    # Additional fields for respondents
    department: Optional[str] = Field(default=None, max_length=100)
    position: Optional[str] = Field(default=None, max_length=100)
    employee_id: Optional[str] = Field(default=None, max_length=50)
    
    # Relationships
    organization: Optional[Organization] = Relationship(back_populates="users")
    responses: List["Response"] = Relationship(back_populates="respondent")


class UserCreate(UserBase):
    """User creation model."""
    password: Optional[str] = Field(default=None, min_length=8)
    org_id: Optional[int] = None
    department: Optional[str] = None
    position: Optional[str] = None
    employee_id: Optional[str] = None


class UserRead(UserBase):
    """User read model."""
    id: int
    org_id: Optional[int]
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    department: Optional[str]
    position: Optional[str]
    employee_id: Optional[str]


class UserUpdate(SQLModel):
    """User update model."""
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    department: Optional[str] = Field(default=None, max_length=100)
    position: Optional[str] = Field(default=None, max_length=100)
    employee_id: Optional[str] = Field(default=None, max_length=50)


# Survey Templates and Questions
class QuestionType(str, Enum):
    """Question types enumeration."""
    RATING = "rating"
    CHOICE = "choice"
    TEXT = "text"
    SOCIOMETRIC = "sociometric"


class QuestionBase(SQLModel):
    """Base question model."""
    text: str = Field(max_length=1000)
    question_type: QuestionType
    options: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    category: Optional[str] = Field(default=None, max_length=100)
    order_index: int = Field(default=0)


class Question(QuestionBase, TimestampMixin, table=True):
    """Question database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    is_active: bool = Field(default=True)
    survey_type: SurveyType


class QuestionCreate(QuestionBase):
    """Question creation model."""
    survey_type: SurveyType


class QuestionRead(QuestionBase):
    """Question read model."""
    id: int
    is_active: bool
    survey_type: SurveyType
    created_at: datetime


# Surveys
class SurveyBase(SQLModel):
    """Base survey model."""
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    survey_type: SurveyType
    anonymize_responses: bool = Field(default=True)


class Survey(SurveyBase, TimestampMixin, table=True):
    """Survey database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: int = Field(foreign_key="organization.id")
    status: SurveyStatus = Field(default=SurveyStatus.DRAFT)
    criteria: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    scheduled_at: Optional[datetime] = Field(default=None)
    activated_at: Optional[datetime] = Field(default=None)
    closed_at: Optional[datetime] = Field(default=None)
    
    # Settings
    reminder_enabled: bool = Field(default=True)
    reminder_days: int = Field(default=3)
    auto_close_days: int = Field(default=14)
    
    # Relationships
    organization: Organization = Relationship(back_populates="surveys")
    responses: List["Response"] = Relationship(back_populates="survey")
    invitations: List["SurveyInvitation"] = Relationship(back_populates="survey")


class SurveyCreate(SurveyBase):
    """Survey creation model."""
    criteria: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    reminder_enabled: Optional[bool] = True
    reminder_days: Optional[int] = 3
    auto_close_days: Optional[int] = 14


class SurveyRead(SurveyBase):
    """Survey read model."""
    id: int
    org_id: int
    status: SurveyStatus
    criteria: Dict[str, Any]
    scheduled_at: Optional[datetime]
    activated_at: Optional[datetime]
    closed_at: Optional[datetime]
    created_at: datetime
    reminder_enabled: bool
    reminder_days: int
    auto_close_days: int


class SurveyUpdate(SQLModel):
    """Survey update model."""
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[SurveyStatus] = None
    scheduled_at: Optional[datetime] = None
    reminder_enabled: Optional[bool] = None
    reminder_days: Optional[int] = None
    auto_close_days: Optional[int] = None


# Survey Invitations
class SurveyInvitationBase(SQLModel):
    """Base survey invitation model."""
    email: EmailStr
    token: str = Field(max_length=500, unique=True)
    expires_at: datetime


class SurveyInvitation(SurveyInvitationBase, TimestampMixin, table=True):
    """Survey invitation database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    survey_id: int = Field(foreign_key="survey.id")
    respondent_id: Optional[int] = Field(default=None, foreign_key="user.id")
    sent_at: Optional[datetime] = Field(default=None)
    opened_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    reminder_count: int = Field(default=0)
    
    # Relationships
    survey: Survey = Relationship(back_populates="invitations")
    respondent: Optional[User] = Relationship()


class SurveyInvitationCreate(SurveyInvitationBase):
    """Survey invitation creation model."""
    survey_id: int
    respondent_id: Optional[int] = None


class SurveyInvitationRead(SurveyInvitationBase):
    """Survey invitation read model."""
    id: int
    survey_id: int
    respondent_id: Optional[int]
    sent_at: Optional[datetime]
    opened_at: Optional[datetime]
    completed_at: Optional[datetime]
    reminder_count: int
    created_at: datetime


# Responses
class ResponseBase(SQLModel):
    """Base response model."""
    answers: Dict[str, Any] = Field(sa_column=Column(JSON))


class Response(ResponseBase, TimestampMixin, table=True):
    """Response database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    survey_id: int = Field(foreign_key="survey.id")
    respondent_id: Optional[int] = Field(default=None, foreign_key="user.id")
    invitation_id: Optional[int] = Field(default=None, foreign_key="surveyinvitation.id")
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    
    # Relationships
    survey: Survey = Relationship(back_populates="responses")
    respondent: Optional[User] = Relationship(back_populates="responses")


class ResponseCreate(ResponseBase):
    """Response creation model."""
    survey_id: int
    respondent_id: Optional[int] = None
    invitation_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ResponseRead(ResponseBase):
    """Response read model."""
    id: int
    survey_id: int
    respondent_id: Optional[int]
    invitation_id: Optional[int]
    submitted_at: datetime
    created_at: datetime


# Payments
class PaymentBase(SQLModel):
    """Base payment model."""
    amount_cents: int
    currency: str = Field(default="EUR", max_length=3)
    team_size: int
    criteria_count: int


class Payment(PaymentBase, TimestampMixin, table=True):
    """Payment database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: int = Field(foreign_key="organization.id")
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    stripe_session_id: Optional[str] = Field(default=None, max_length=200, unique=True)
    stripe_payment_intent_id: Optional[str] = Field(default=None, max_length=200)
    paid_at: Optional[datetime] = Field(default=None)
    refunded_at: Optional[datetime] = Field(default=None)
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    # Relationships
    organization: Organization = Relationship(back_populates="payments")


class PaymentCreate(PaymentBase):
    """Payment creation model."""
    org_id: int
    stripe_session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentRead(PaymentBase):
    """Payment read model."""
    id: int
    org_id: int
    status: PaymentStatus
    stripe_session_id: Optional[str]
    stripe_payment_intent_id: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime


# Analytics Models
class AnalyticsSnapshot(SQLModel, table=True):
    """Analytics snapshot for caching complex calculations."""
    id: Optional[int] = Field(default=None, primary_key=True)
    survey_id: int = Field(foreign_key="survey.id")
    snapshot_type: str = Field(max_length=50)  # 'network', 'metrics', 'insights'
    data: Dict[str, Any] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)


# Team Import Models
class TeamImportBase(SQLModel):
    """Base team import model."""
    filename: str = Field(max_length=255)
    total_emails: int
    processed_emails: int
    failed_emails: int


class TeamImport(TeamImportBase, TimestampMixin, table=True):
    """Team import database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: int = Field(foreign_key="organization.id")
    status: str = Field(max_length=50)  # 'processing', 'completed', 'failed'
    errors: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    # Relationships
    organization: Organization = Relationship()


class TeamImportCreate(TeamImportBase):
    """Team import creation model."""
    org_id: int
    status: str = "processing"
    errors: Optional[Dict[str, Any]] = None


class TeamImportRead(TeamImportBase):
    """Team import read model."""
    id: int
    org_id: int
    status: str
    errors: Optional[Dict[str, Any]]
    created_at: datetime