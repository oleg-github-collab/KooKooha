"""Survey management routes."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from pydantic import BaseModel, validator
import structlog

from ..database import get_session
from ..models import (
    Survey, SurveyCreate, SurveyRead, SurveyUpdate, SurveyStatus, SurveyType,
    SurveyInvitation, SurveyInvitationCreate, SurveyInvitationRead,
    User, UserRole, Organization, Question, QuestionRead
)
from ..auth import (
    get_current_user, verify_organization_access, require_client_admin,
    create_survey_token, verify_survey_token
)
from ..services.email_service import EmailService
from ..services.survey_service import SurveyService
from ..config import settings


logger = structlog.get_logger()
router = APIRouter()


class SurveyCreateRequest(BaseModel):
    """Survey creation request model."""
    title: str
    description: Optional[str] = None
    survey_type: SurveyType
    criteria: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    anonymize_responses: bool = True
    reminder_enabled: bool = True
    reminder_days: int = 3
    auto_close_days: int = 14
    
    @validator('scheduled_at')
    def validate_scheduled_at(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('Scheduled time must be in the future')
        return v


class SurveyActivateRequest(BaseModel):
    """Survey activation request model."""
    send_invitations: bool = True
    custom_message: Optional[str] = None


class SurveyInviteRequest(BaseModel):
    """Survey invitation request model."""
    user_ids: Optional[List[int]] = None
    send_to_all: bool = False
    custom_message: Optional[str] = None


class SurveyTokenVerification(BaseModel):
    """Survey token verification response."""
    survey_id: int
    survey_title: str
    survey_description: Optional[str]
    survey_type: SurveyType
    is_valid: bool
    expires_at: datetime
    already_completed: bool = False


@router.post("/", response_model=SurveyRead)
async def create_survey(
    survey_data: SurveyCreateRequest,
    org_id: int = Query(..., description="Organization ID"),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_client_admin)
):
    """Create a new survey."""
    # Verify organization access
    await verify_organization_access(org_id, current_user)
    
    logger.info(
        "Creating survey",
        org_id=org_id,
        survey_type=survey_data.survey_type,
        user_id=current_user.id
    )
    
    # Create survey
    survey = Survey(
        title=survey_data.title,
        description=survey_data.description,
        survey_type=survey_data.survey_type,
        org_id=org_id,
        criteria=survey_data.criteria or {},
        scheduled_at=survey_data.scheduled_at,
        anonymize_responses=survey_data.anonymize_responses,
        reminder_enabled=survey_data.reminder_enabled,
        reminder_days=survey_data.reminder_days,
        auto_close_days=survey_data.auto_close_days,
        status=SurveyStatus.DRAFT
    )
    
    session.add(survey)
    session.commit()
    session.refresh(survey)
    
    logger.info("Survey created", survey_id=survey.id, org_id=org_id)
    
    return SurveyRead.model_validate(survey)


@router.get("/", response_model=List[SurveyRead])
async def get_surveys(
    org_id: int = Query(..., description="Organization ID"),
    status: Optional[SurveyStatus] = Query(None, description="Filter by status"),
    survey_type: Optional[SurveyType] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get surveys for organization."""
    # Verify organization access
    await verify_organization_access(org_id, current_user)
    
    # Build query
    query = select(Survey).where(Survey.org_id == org_id)
    
    if status:
        query = query.where(Survey.status == status)
    
    if survey_type:
        query = query.where(Survey.survey_type == survey_type)
    
    query = query.order_by(Survey.created_at.desc()).offset(offset).limit(limit)
    
    surveys = session.exec(query).all()
    return [SurveyRead.model_validate(survey) for survey in surveys]


@router.get("/{survey_id}", response_model=SurveyRead)
async def get_survey(
    survey_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get survey details."""
    survey = session.get(Survey, survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Verify organization access
    await verify_organization_access(survey.org_id, current_user)
    
    return SurveyRead.model_validate(survey)


@router.put("/{survey_id}", response_model=SurveyRead)
async def update_survey(
    survey_id: int,
    update_data: SurveyUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_client_admin)
):
    """Update survey."""
    survey = session.get(Survey, survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Verify organization access
    await verify_organization_access(survey.org_id, current_user)
    
    # Check if survey can be updated
    if survey.status in [SurveyStatus.ACTIVE, SurveyStatus.CLOSED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update active or closed surveys"
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(survey, field, value)
    
    survey.updated_at = datetime.utcnow()
    session.add(survey)
    session.commit()
    session.refresh(survey)
    
    logger.info("Survey updated", survey_id=survey_id, updated_by=current_user.id)
    
    return SurveyRead.model_validate(survey)


@router.post("/{survey_id}/activate")
async def activate_survey(
    survey_id: int,
    activation_data: SurveyActivateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_client_admin)
):
    """Activate survey and send invitations."""
    survey = session.get(Survey, survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Verify organization access
    await verify_organization_access(survey.org_id, current_user)
    
    # Check if survey can be activated
    if survey.status != SurveyStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft surveys can be activated"
        )
    
    try:
        # Activate survey
        survey.status = SurveyStatus.ACTIVE
        survey.activated_at = datetime.utcnow()
        session.add(survey)
        session.commit()
        
        logger.info("Survey activated", survey_id=survey_id, activated_by=current_user.id)
        
        # Send invitations if requested
        if activation_data.send_invitations:
            survey_service = SurveyService(session)
            invitation_result = await survey_service.send_survey_invitations(
                survey_id=survey_id,
                custom_message=activation_data.custom_message
            )
            
            logger.info(
                "Survey invitations sent",
                survey_id=survey_id,
                invitations_sent=invitation_result.get('sent', 0),
                invitations_failed=invitation_result.get('failed', 0)
            )
            
            return {
                "message": "Survey activated and invitations sent",
                "survey_id": survey_id,
                "invitations_sent": invitation_result.get('sent', 0),
                "invitations_failed": invitation_result.get('failed', 0)
            }
        
        return {
            "message": "Survey activated",
            "survey_id": survey_id
        }
        
    except Exception as e:
        session.rollback()
        logger.error("Failed to activate survey", survey_id=survey_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate survey: {str(e)}"
        )


@router.post("/{survey_id}/invite")
async def send_survey_invitations(
    survey_id: int,
    invite_data: SurveyInviteRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_client_admin)
):
    """Send survey invitations to specific users or all team members."""
    survey = session.get(Survey, survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Verify organization access
    await verify_organization_access(survey.org_id, current_user)
    
    # Check if survey is active
    if survey.status != SurveyStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Survey must be active to send invitations"
        )
    
    try:
        survey_service = SurveyService(session)
        
        if invite_data.send_to_all:
            # Send to all team members
            result = await survey_service.send_survey_invitations(
                survey_id=survey_id,
                custom_message=invite_data.custom_message
            )
        else:
            # Send to specific users
            if not invite_data.user_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User IDs required when not sending to all"
                )
            
            result = await survey_service.send_survey_invitations(
                survey_id=survey_id,
                user_ids=invite_data.user_ids,
                custom_message=invite_data.custom_message
            )
        
        logger.info(
            "Survey invitations sent",
            survey_id=survey_id,
            sent=result.get('sent', 0),
            failed=result.get('failed', 0)
        )
        
        return {
            "message": "Invitations sent",
            "sent": result.get('sent', 0),
            "failed": result.get('failed', 0),
            "errors": result.get('errors', [])
        }
        
    except Exception as e:
        logger.error("Failed to send invitations", survey_id=survey_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send invitations: {str(e)}"
        )


@router.post("/{survey_id}/close")
async def close_survey(
    survey_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_client_admin)
):
    """Close survey."""
    survey = session.get(Survey, survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Verify organization access
    await verify_organization_access(survey.org_id, current_user)
    
    # Check if survey can be closed
    if survey.status != SurveyStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active surveys can be closed"
        )
    
    # Close survey
    survey.status = SurveyStatus.CLOSED
    survey.closed_at = datetime.utcnow()
    session.add(survey)
    session.commit()
    
    logger.info("Survey closed", survey_id=survey_id, closed_by=current_user.id)
    
    return {
        "message": "Survey closed",
        "survey_id": survey_id,
        "closed_at": survey.closed_at
    }


@router.delete("/{survey_id}")
async def delete_survey(
    survey_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_client_admin)
):
    """Delete survey (only if draft)."""
    survey = session.get(Survey, survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Verify organization access
    await verify_organization_access(survey.org_id, current_user)
    
    # Check if survey can be deleted
    if survey.status != SurveyStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft surveys can be deleted"
        )
    
    # Delete survey
    session.delete(survey)
    session.commit()
    
    logger.info("Survey deleted", survey_id=survey_id, deleted_by=current_user.id)
    
    return {"message": "Survey deleted"}


@router.get("/{survey_id}/invitations", response_model=List[SurveyInvitationRead])
async def get_survey_invitations(
    survey_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get survey invitations."""
    survey = session.get(Survey, survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Verify organization access
    await verify_organization_access(survey.org_id, current_user)
    
    # Get invitations
    query = select(SurveyInvitation).where(
        SurveyInvitation.survey_id == survey_id
    ).order_by(SurveyInvitation.created_at.desc())
    
    invitations = session.exec(query).all()
    return [SurveyInvitationRead.model_validate(invitation) for invitation in invitations]


@router.get("/{survey_id}/stats")
async def get_survey_stats(
    survey_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get survey statistics."""
    survey = session.get(Survey, survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Verify organization access
    await verify_organization_access(survey.org_id, current_user)
    
    # Calculate stats
    query = select(SurveyInvitation).where(SurveyInvitation.survey_id == survey_id)
    invitations = session.exec(query).all()
    
    total_invitations = len(invitations)
    completed = len([i for i in invitations if i.completed_at])
    opened = len([i for i in invitations if i.opened_at])
    
    response_rate = (completed / total_invitations * 100) if total_invitations > 0 else 0
    open_rate = (opened / total_invitations * 100) if total_invitations > 0 else 0
    
    return {
        "survey_id": survey_id,
        "status": survey.status,
        "total_invitations": total_invitations,
        "completed_responses": completed,
        "opened_invitations": opened,
        "response_rate": round(response_rate, 2),
        "open_rate": round(open_rate, 2),
        "created_at": survey.created_at,
        "activated_at": survey.activated_at,
        "closed_at": survey.closed_at
    }


# Public endpoints for survey participation

@router.get("/link/{token}", response_model=SurveyTokenVerification)
async def verify_survey_link(
    token: str,
    session: Session = Depends(get_session)
):
    """Verify survey invitation token and return survey details."""
    try:
        # Verify token
        payload = await verify_survey_token(token, session)
        survey_id = payload.get('survey_id')
        invitation_id = payload.get('invitation_id')
        
        # Get survey
        survey = session.get(Survey, survey_id)
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Survey not found"
            )
        
        # Check if survey is active
        if survey.status != SurveyStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Survey is not currently active"
            )
        
        # Check if already completed
        already_completed = False
        if invitation_id:
            invitation = session.get(SurveyInvitation, invitation_id)
            if invitation and invitation.completed_at:
                already_completed = True
        
        logger.info(
            "Survey link verified",
            survey_id=survey_id,
            invitation_id=invitation_id,
            already_completed=already_completed
        )
        
        return SurveyTokenVerification(
            survey_id=survey.id,
            survey_title=survey.title,
            survey_description=survey.description,
            survey_type=survey.survey_type,
            is_valid=True,
            expires_at=payload.get('exp'),
            already_completed=already_completed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to verify survey token", token=token[:20] + "...", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired survey link"
        )


@router.get("/types", response_model=List[Dict[str, Any]])
async def get_survey_types():
    """Get available survey types and their descriptions."""
    survey_types = [
        {
            "type": SurveyType.SOCIOMETRY,
            "name": "Sociometric Analysis",
            "description": "Analyze team relationships and communication patterns",
            "estimated_time": "10-15 minutes",
            "features": ["Team dynamics mapping", "Communication flow analysis", "Influence networks"]
        },
        {
            "type": SurveyType.REVIEW_360,
            "name": "360-Degree Review",
            "description": "Comprehensive feedback from peers, subordinates, and supervisors",
            "estimated_time": "15-20 minutes",
            "features": ["Multi-source feedback", "Leadership assessment", "Development insights"]
        },
        {
            "type": SurveyType.ENPS,
            "name": "Employee Net Promoter Score",
            "description": "Measure employee loyalty and engagement",
            "estimated_time": "5-8 minutes",
            "features": ["Engagement scoring", "Loyalty metrics", "Satisfaction tracking"]
        },
        {
            "type": SurveyType.TEAM_DYNAMICS,
            "name": "Team Dynamics Assessment",
            "description": "Evaluate team collaboration and effectiveness",
            "estimated_time": "12-18 minutes",
            "features": ["Collaboration analysis", "Team cohesion", "Performance indicators"]
        }
    ]
    
    return survey_types


@router.get("/questions/{survey_type}", response_model=List[QuestionRead])
async def get_survey_questions(
    survey_type: SurveyType,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get available questions for a survey type."""
    query = select(Question).where(
        Question.survey_type == survey_type,
        Question.is_active == True
    ).order_by(Question.order_index)
    
    questions = session.exec(query).all()
    return [QuestionRead.model_validate(question) for question in questions]
