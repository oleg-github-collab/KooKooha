"""Admin routes for SuperAdmin functionality."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func
from pydantic import BaseModel, EmailStr
import structlog

from ..database import get_session
from ..models import (
    User, UserRead, UserCreate, UserUpdate, UserRole,
    Organization, OrganizationRead, OrganizationCreate, OrganizationUpdate,
    Survey, SurveyRead, Payment, PaymentRead,
    Question, QuestionCreate, QuestionRead, QuestionUpdate,
    Response, TeamImport
)
from ..auth import require_superadmin, get_current_user
from ..config import settings


logger = structlog.get_logger()
router = APIRouter()


class AdminStats(BaseModel):
    """Admin dashboard statistics."""
    total_organizations: int
    total_users: int
    total_surveys: int
    total_responses: int
    total_revenue_eur: float
    active_surveys: int
    new_orgs_this_month: int
    response_rate_avg: float


class UserCreateAdmin(BaseModel):
    """Admin user creation model."""
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: UserRole
    org_id: Optional[int] = None
    is_active: bool = True
    department: Optional[str] = None
    position: Optional[str] = None


class OrganizationAdmin(BaseModel):
    """Admin organization model with extra details."""
    id: int
    name: str
    description: Optional[str]
    website: Optional[str]
    industry: Optional[str]
    is_active: bool
    created_at: datetime
    user_count: int
    survey_count: int
    total_revenue_eur: float
    last_activity: Optional[datetime]


@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Get admin dashboard statistics."""
    # Total counts
    total_orgs = len(session.exec(select(Organization)).all())
    total_users = len(session.exec(select(User)).all())
    total_surveys = len(session.exec(select(Survey)).all())
    total_responses = len(session.exec(select(Response)).all())
    
    # Active surveys
    active_surveys = len(session.exec(
        select(Survey).where(Survey.status == "active")
    ).all())
    
    # Revenue calculation
    completed_payments = session.exec(
        select(Payment).where(Payment.status == "completed")
    ).all()
    total_revenue = sum(p.amount_cents for p in completed_payments) / 100
    
    # New organizations this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_orgs_this_month = len(session.exec(
        select(Organization).where(Organization.created_at >= month_start)
    ).all())
    
    # Average response rate
    survey_stats = []
    for survey in session.exec(select(Survey)).all():
        from ..models import SurveyInvitation
        invitations = session.exec(
            select(SurveyInvitation).where(SurveyInvitation.survey_id == survey.id)
        ).all()
        responses = session.exec(
            select(Response).where(Response.survey_id == survey.id)
        ).all()
        
        if invitations:
            response_rate = len(responses) / len(invitations) * 100
            survey_stats.append(response_rate)
    
    avg_response_rate = sum(survey_stats) / len(survey_stats) if survey_stats else 0
    
    return AdminStats(
        total_organizations=total_orgs,
        total_users=total_users,
        total_surveys=total_surveys,
        total_responses=total_responses,
        total_revenue_eur=total_revenue,
        active_surveys=active_surveys,
        new_orgs_this_month=new_orgs_this_month,
        response_rate_avg=round(avg_response_rate, 2)
    )


@router.get("/organizations", response_model=List[OrganizationAdmin])
async def get_all_organizations(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Get all organizations with admin details."""
    query = select(Organization)
    
    if search:
        query = query.where(Organization.name.contains(search))
    
    query = query.order_by(Organization.created_at.desc()).offset(offset).limit(limit)
    organizations = session.exec(query).all()
    
    result = []
    for org in organizations:
        # Count users
        user_count = len(session.exec(
            select(User).where(User.org_id == org.id, User.is_active == True)
        ).all())
        
        # Count surveys
        survey_count = len(session.exec(
            select(Survey).where(Survey.org_id == org.id)
        ).all())
        
        # Calculate revenue
        payments = session.exec(
            select(Payment).where(
                Payment.org_id == org.id,
                Payment.status == "completed"
            )
        ).all()
        total_revenue = sum(p.amount_cents for p in payments) / 100
        
        # Get last activity
        last_survey = session.exec(
            select(Survey).where(Survey.org_id == org.id)
            .order_by(Survey.created_at.desc())
        ).first()
        last_activity = last_survey.created_at if last_survey else None
        
        result.append(OrganizationAdmin(
            id=org.id,
            name=org.name,
            description=org.description,
            website=org.website,
            industry=org.industry,
            is_active=org.is_active,
            created_at=org.created_at,
            user_count=user_count,
            survey_count=survey_count,
            total_revenue_eur=total_revenue,
            last_activity=last_activity
        ))
    
    return result


@router.post("/organizations", response_model=OrganizationRead)
async def create_organization_admin(
    org_data: OrganizationCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Create organization as admin."""
    organization = Organization.model_validate(org_data)
    session.add(organization)
    session.commit()
    session.refresh(organization)
    
    logger.info(
        "Organization created by admin",
        org_id=organization.id,
        name=organization.name,
        created_by=current_user.id
    )
    
    return OrganizationRead.model_validate(organization)


@router.put("/organizations/{org_id}", response_model=OrganizationRead)
async def update_organization_admin(
    org_id: int,
    update_data: OrganizationUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Update organization as admin."""
    organization = session.get(Organization, org_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(organization, field, value)
    
    organization.updated_at = datetime.utcnow()
    session.add(organization)
    session.commit()
    session.refresh(organization)
    
    logger.info(
        "Organization updated by admin",
        org_id=org_id,
        updated_by=current_user.id
    )
    
    return OrganizationRead.model_validate(organization)


@router.delete("/organizations/{org_id}")
async def delete_organization_admin(
    org_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Delete organization and all related data."""
    organization = session.get(Organization, org_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Mark as inactive instead of hard delete to preserve data integrity
    organization.is_active = False
    organization.updated_at = datetime.utcnow()
    
    # Also mark all users as inactive
    users = session.exec(select(User).where(User.org_id == org_id)).all()
    for user in users:
        user.is_active = False
        user.updated_at = datetime.utcnow()
        session.add(user)
    
    session.add(organization)
    session.commit()
    
    logger.info(
        "Organization deactivated by admin",
        org_id=org_id,
        deleted_by=current_user.id
    )
    
    return {"message": "Organization deactivated successfully"}


@router.get("/users", response_model=List[UserRead])
async def get_all_users(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    role: Optional[UserRole] = Query(None),
    search: Optional[str] = Query(None),
    org_id: Optional[int] = Query(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Get all users with filtering options."""
    query = select(User)
    
    if role:
        query = query.where(User.role == role)
    
    if org_id:
        query = query.where(User.org_id == org_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (User.email.contains(search)) |
            (User.first_name.contains(search)) |
            (User.last_name.contains(search))
        )
    
    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    users = session.exec(query).all()
    
    return [UserRead.model_validate(user) for user in users]


@router.post("/users", response_model=UserRead)
async def create_user_admin(
    user_data: UserCreateAdmin,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Create user as admin."""
    # Check if email already exists
    existing_user = session.exec(
        select(User).where(User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Validate organization if specified
    if user_data.org_id:
        org = session.get(Organization, user_data.org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization not found"
            )
    
    from ..auth import get_password_hash
    
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        org_id=user_data.org_id,
        is_active=user_data.is_active,
        department=user_data.department,
        position=user_data.position,
        is_verified=True  # Admin-created users are auto-verified
    )
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    logger.info(
        "User created by admin",
        user_id=user.id,
        email=user.email,
        role=user.role,
        created_by=current_user.id
    )
    
    return UserRead.model_validate(user)


@router.put("/users/{user_id}", response_model=UserRead)
async def update_user_admin(
    user_id: int,
    update_data: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Update user as admin."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)
    
    logger.info(
        "User updated by admin",
        user_id=user_id,
        updated_by=current_user.id
    )
    
    return UserRead.model_validate(user)


@router.delete("/users/{user_id}")
async def delete_user_admin(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Deactivate user."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting other superadmins
    if user.role == UserRole.SUPERADMIN and user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete other superadmin users"
        )
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    
    logger.info(
        "User deactivated by admin",
        user_id=user_id,
        deleted_by=current_user.id
    )
    
    return {"message": "User deactivated successfully"}


@router.get("/surveys", response_model=List[SurveyRead])
async def get_all_surveys_admin(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    org_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Get all surveys across organizations."""
    query = select(Survey)
    
    if org_id:
        query = query.where(Survey.org_id == org_id)
    
    if status:
        query = query.where(Survey.status == status)
    
    query = query.order_by(Survey.created_at.desc()).offset(offset).limit(limit)
    surveys = session.exec(query).all()
    
    return [SurveyRead.model_validate(survey) for survey in surveys]


@router.get("/payments", response_model=List[PaymentRead])
async def get_all_payments_admin(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    org_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Get all payments across organizations."""
    query = select(Payment)
    
    if org_id:
        query = query.where(Payment.org_id == org_id)
    
    if status:
        query = query.where(Payment.status == status)
    
    query = query.order_by(Payment.created_at.desc()).offset(offset).limit(limit)
    payments = session.exec(query).all()
    
    return [PaymentRead.model_validate(payment) for payment in payments]


@router.get("/questions", response_model=List[QuestionRead])
async def get_all_questions(
    survey_type: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Get all survey questions."""
    query = select(Question).where(Question.is_active == True)
    
    if survey_type:
        query = query.where(Question.survey_type == survey_type)
    
    query = query.order_by(Question.survey_type, Question.order_index)
    questions = session.exec(query).all()
    
    return [QuestionRead.model_validate(question) for question in questions]


@router.post("/questions", response_model=QuestionRead)
async def create_question(
    question_data: QuestionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Create new survey question."""
    question = Question.model_validate(question_data)
    session.add(question)
    session.commit()
    session.refresh(question)
    
    logger.info(
        "Question created by admin",
        question_id=question.id,
        survey_type=question.survey_type,
        created_by=current_user.id
    )
    
    return QuestionRead.model_validate(question)


@router.put("/questions/{question_id}", response_model=QuestionRead)
async def update_question(
    question_id: int,
    update_data: QuestionUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Update survey question."""
    question = session.get(Question, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(question, field, value)
    
    question.updated_at = datetime.utcnow()
    session.add(question)
    session.commit()
    session.refresh(question)
    
    logger.info(
        "Question updated by admin",
        question_id=question_id,
        updated_by=current_user.id
    )
    
    return QuestionRead.model_validate(question)


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Deactivate survey question."""
    question = session.get(Question, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    question.is_active = False
    question.updated_at = datetime.utcnow()
    session.add(question)
    session.commit()
    
    logger.info(
        "Question deactivated by admin",
        question_id=question_id,
        deleted_by=current_user.id
    )
    
    return {"message": "Question deactivated successfully"}


@router.get("/analytics/overview")
async def get_platform_analytics(
    period_days: int = Query(30, ge=1, le=365),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Get platform-wide analytics."""
    cutoff_date = datetime.utcnow() - timedelta(days=period_days)
    
    # Organizations growth
    new_orgs = session.exec(
        select(Organization).where(Organization.created_at >= cutoff_date)
    ).all()
    
    # User growth
    new_users = session.exec(
        select(User).where(User.created_at >= cutoff_date)
    ).all()
    
    # Survey activity
    new_surveys = session.exec(
        select(Survey).where(Survey.created_at >= cutoff_date)
    ).all()
    
    # Revenue
    revenue_payments = session.exec(
        select(Payment).where(
            Payment.created_at >= cutoff_date,
            Payment.status == "completed"
        )
    ).all()
    
    total_revenue = sum(p.amount_cents for p in revenue_payments) / 100
    
    # Group by day for trends
    daily_stats = {}
    
    for org in new_orgs:
        date_key = org.created_at.date().isoformat()
        if date_key not in daily_stats:
            daily_stats[date_key] = {"orgs": 0, "users": 0, "surveys": 0, "revenue": 0}
        daily_stats[date_key]["orgs"] += 1
    
    for user in new_users:
        date_key = user.created_at.date().isoformat()
        if date_key not in daily_stats:
            daily_stats[date_key] = {"orgs": 0, "users": 0, "surveys": 0, "revenue": 0}
        daily_stats[date_key]["users"] += 1
    
    for survey in new_surveys:
        date_key = survey.created_at.date().isoformat()
        if date_key not in daily_stats:
            daily_stats[date_key] = {"orgs": 0, "users": 0, "surveys": 0, "revenue": 0}
        daily_stats[date_key]["surveys"] += 1
    
    for payment in revenue_payments:
        date_key = payment.created_at.date().isoformat()
        if date_key not in daily_stats:
            daily_stats[date_key] = {"orgs": 0, "users": 0, "surveys": 0, "revenue": 0}
        daily_stats[date_key]["revenue"] += payment.amount_cents / 100
    
    return {
        "period_days": period_days,
        "summary": {
            "new_organizations": len(new_orgs),
            "new_users": len(new_users),
            "new_surveys": len(new_surveys),
            "total_revenue_eur": total_revenue
        },
        "daily_stats": daily_stats
    }


@router.post("/system/cleanup")
async def cleanup_system_data(
    days_old: int = Query(365, ge=30, description="Delete data older than X days"),
    dry_run: bool = Query(True, description="Preview changes without deleting"),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_superadmin)
):
    """Clean up old system data."""
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    # Find old data
    old_team_imports = session.exec(
        select(TeamImport).where(TeamImport.created_at < cutoff_date)
    ).all()
    
    # Find old analytics snapshots
    from ..models import AnalyticsSnapshot
    old_snapshots = session.exec(
        select(AnalyticsSnapshot).where(AnalyticsSnapshot.created_at < cutoff_date)
    ).all()
    
    cleanup_summary = {
        "team_imports_to_delete": len(old_team_imports),
        "analytics_snapshots_to_delete": len(old_snapshots),
        "cutoff_date": cutoff_date.isoformat(),
        "dry_run": dry_run
    }
    
    if not dry_run:
        # Perform actual cleanup
        for item in old_team_imports:
            session.delete(item)
        
        for item in old_snapshots:
            session.delete(item)
        
        session.commit()
        
        logger.info(
            "System cleanup performed",
            deleted_imports=len(old_team_imports),
            deleted_snapshots=len(old_snapshots),
            performed_by=current_user.id
        )
        
        cleanup_summary["status"] = "completed"
    else:
        cleanup_summary["status"] = "preview_only"
    
    return cleanup_summary