"""Survey service for managing survey operations."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from sqlmodel import Session, select
import structlog

from ..models import (
    Survey, SurveyInvitation, User, UserRole, Organization,
    Response, SurveyStatus
)
from ..auth import create_survey_token
from ..config import settings
from .email_service import EmailService


logger = structlog.get_logger()


class SurveyService:
    """Service for survey operations."""
    
    def __init__(self, session: Session):
        self.session = session
        self.email_service = EmailService()
    
    async def send_survey_invitations(
        self,
        survey_id: int,
        user_ids: Optional[List[int]] = None,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send survey invitations to users."""
        # Get survey
        survey = self.session.get(Survey, survey_id)
        if not survey:
            raise ValueError("Survey not found")
        
        # Get organization
        organization = self.session.get(Organization, survey.org_id)
        if not organization:
            raise ValueError("Organization not found")
        
        # Determine target users
        if user_ids:
            # Send to specific users
            query = select(User).where(
                User.id.in_(user_ids),
                User.org_id == survey.org_id,
                User.is_active == True,
                User.role == UserRole.RESPONDENT
            )
        else:
            # Send to all respondents in organization
            query = select(User).where(
                User.org_id == survey.org_id,
                User.is_active == True,
                User.role == UserRole.RESPONDENT
            )
        
        users = self.session.exec(query).all()
        
        sent = 0
        failed = 0
        errors = []
        
        for user in users:
            try:
                # Check if invitation already exists
                existing_invitation = self.session.exec(
                    select(SurveyInvitation).where(
                        SurveyInvitation.survey_id == survey_id,
                        SurveyInvitation.respondent_id == user.id
                    )
                ).first()
                
                if existing_invitation:
                    # Update existing invitation
                    invitation = existing_invitation
                    # Reset sent timestamp to allow resending
                    invitation.sent_at = None
                    invitation.reminder_count = 0
                else:
                    # Create new invitation
                    invitation = await self._create_survey_invitation(survey_id, user)
                
                # Send email
                success = await self._send_invitation_email(
                    survey=survey,
                    invitation=invitation,
                    user=user,
                    organization=organization,
                    custom_message=custom_message
                )
                
                if success:
                    invitation.sent_at = datetime.utcnow()
                    self.session.add(invitation)
                    sent += 1
                    logger.info(f"Invitation sent to {user.email}")
                else:
                    failed += 1
                    errors.append({
                        "email": user.email,
                        "error": "Failed to send email"
                    })
                    logger.error(f"Failed to send invitation to {user.email}")
                
            except Exception as e:
                failed += 1
                errors.append({
                    "email": user.email,
                    "error": str(e)
                })
                logger.error(f"Error sending invitation to {user.email}: {str(e)}")
        
        # Commit all changes
        self.session.commit()
        
        logger.info(
            "Survey invitations processed",
            survey_id=survey_id,
            sent=sent,
            failed=failed,
            total_users=len(users)
        )
        
        return {
            "sent": sent,
            "failed": failed,
            "errors": errors,
            "total_users": len(users)
        }
    
    async def _create_survey_invitation(self, survey_id: int, user: User) -> SurveyInvitation:
        """Create a survey invitation."""
        # Create survey token
        token = create_survey_token(
            survey_id=survey_id,
            respondent_id=user.id
        )
        
        # Calculate expiration date
        expires_at = datetime.utcnow() + timedelta(days=settings.survey_token_expire_days)
        
        # Create invitation
        invitation = SurveyInvitation(
            survey_id=survey_id,
            respondent_id=user.id,
            email=user.email,
            token=token,
            expires_at=expires_at
        )
        
        self.session.add(invitation)
        self.session.commit()
        self.session.refresh(invitation)
        
        # Update token with invitation ID
        token = create_survey_token(
            survey_id=survey_id,
            respondent_id=user.id,
            invitation_id=invitation.id
        )
        
        invitation.token = token
        self.session.add(invitation)
        self.session.commit()
        
        return invitation
    
    async def _send_invitation_email(
        self,
        survey: Survey,
        invitation: SurveyInvitation,
        user: User,
        organization: Organization,
        custom_message: Optional[str] = None
    ) -> bool:
        """Send invitation email to user."""
        # Create survey link
        survey_link = settings.survey_url_template.format(token=invitation.token)
        
        # Calculate estimated time based on survey type
        estimated_times = {
            "sociometry": "10-15",
            "360": "15-20",
            "enps": "5-8",
            "team_dynamics": "12-18"
        }
        estimated_time = estimated_times.get(survey.survey_type, "10-15")
        
        # Calculate expiration date
        expires_at = invitation.expires_at
        
        # Send email
        return await self.email_service.send_survey_invitation(
            to_email=user.email,
            survey_title=survey.title,
            survey_link=survey_link,
            first_name=user.first_name,
            survey_description=custom_message or survey.description,
            estimated_time=estimated_time,
            expires_at=expires_at
        )
    
    async def send_survey_reminders(self, survey_id: int) -> Dict[str, Any]:
        """Send reminder emails for incomplete surveys."""
        # Get survey
        survey = self.session.get(Survey, survey_id)
        if not survey:
            raise ValueError("Survey not found")
        
        if not survey.reminder_enabled:
            return {"sent": 0, "message": "Reminders disabled for this survey"}
        
        # Get incomplete invitations
        query = select(SurveyInvitation).where(
            SurveyInvitation.survey_id == survey_id,
            SurveyInvitation.completed_at.is_(None),
            SurveyInvitation.sent_at.isnot(None),
            SurveyInvitation.expires_at > datetime.utcnow()
        )
        
        invitations = self.session.exec(query).all()
        
        sent = 0
        failed = 0
        errors = []
        
        for invitation in invitations:
            try:
                # Check if reminder should be sent
                days_since_sent = (datetime.utcnow() - invitation.sent_at).days
                
                if days_since_sent >= survey.reminder_days and invitation.reminder_count < 2:
                    # Get user and organization
                    user = self.session.get(User, invitation.respondent_id)
                    organization = self.session.get(Organization, survey.org_id)
                    
                    if user and organization:
                        # Send reminder email
                        success = await self._send_reminder_email(
                            survey=survey,
                            invitation=invitation,
                            user=user,
                            organization=organization
                        )
                        
                        if success:
                            invitation.reminder_count += 1
                            self.session.add(invitation)
                            sent += 1
                        else:
                            failed += 1
                            errors.append({
                                "email": invitation.email,
                                "error": "Failed to send reminder email"
                            })
                
            except Exception as e:
                failed += 1
                errors.append({
                    "email": invitation.email,
                    "error": str(e)
                })
                logger.error(f"Error sending reminder: {str(e)}")
        
        # Commit changes
        self.session.commit()
        
        logger.info(
            "Survey reminders processed",
            survey_id=survey_id,
            sent=sent,
            failed=failed
        )
        
        return {
            "sent": sent,
            "failed": failed,
            "errors": errors
        }
    
    async def _send_reminder_email(
        self,
        survey: Survey,
        invitation: SurveyInvitation,
        user: User,
        organization: Organization
    ) -> bool:
        """Send reminder email."""
        # Create survey link
        survey_link = settings.survey_url_template.format(token=invitation.token)
        
        # Calculate estimated time
        estimated_times = {
            "sociometry": "10-15",
            "360": "15-20",
            "enps": "5-8",
            "team_dynamics": "12-18"
        }
        estimated_time = estimated_times.get(survey.survey_type, "10-15")
        
        # Send reminder email (using a custom template for reminders)
        subject = f"Reminder: {survey.title} - Response Needed"
        
        text_content = f"""
Hello {user.first_name or 'Team Member'},

This is a friendly reminder that you have a pending survey to complete: {survey.title}

{survey.description or ''}

To participate, please click the link below:
{survey_link}

This survey will take approximately {estimated_time} minutes to complete.

The survey will close on {invitation.expires_at.strftime('%B %d, %Y') if invitation.expires_at else 'soon'}.

Your participation is important for improving our workplace culture.

Best regards,
The Kookooha Team
"""
        
        html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #6366f1;">Kookooha</h1>
            <p style="color: #666;">Mental Health & Corporate Culture</p>
        </div>
        
        <h2 style="color: #dc2626;">⏰ Survey Reminder</h2>
        
        <p>Hello {user.first_name or 'Team Member'},</p>
        
        <p>This is a friendly reminder that you have a pending survey to complete:</p>
        
        <div style="background: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b;">
            <h3 style="margin-top: 0; color: #92400e;">{survey.title}</h3>
            {"<p>" + survey.description + "</p>" if survey.description else ""}
            <p><strong>Estimated time:</strong> {estimated_time} minutes</p>
            {"<p><strong>Closes on:</strong> " + invitation.expires_at.strftime('%B %d, %Y') + "</p>" if invitation.expires_at else ""}
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{survey_link}" 
               style="background: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                Complete Survey Now
            </a>
        </div>
        
        <p>Your participation is important for improving our workplace culture and wellbeing.</p>
        
        <p>Best regards,<br>The Kookooha Team</p>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
        <p style="font-size: 12px; color: #666; text-align: center;">
            This is an automated reminder. If you have already completed the survey, please disregard this message.
        </p>
    </div>
</body>
</html>
"""
        
        return await self.email_service.send_email(
            to_email=user.email,
            subject=subject,
            text_content=text_content,
            html_content=html_content,
            to_name=user.first_name
        )
    
    async def auto_close_expired_surveys(self) -> Dict[str, Any]:
        """Automatically close surveys that have reached their auto-close date."""
        # Find surveys that should be auto-closed
        cutoff_date = datetime.utcnow()
        
        query = select(Survey).where(
            Survey.status == SurveyStatus.ACTIVE,
            Survey.activated_at.isnot(None)
        )
        
        surveys = self.session.exec(query).all()
        closed_count = 0
        
        for survey in surveys:
            if survey.activated_at:
                # Calculate auto-close date
                auto_close_date = survey.activated_at + timedelta(days=survey.auto_close_days)
                
                if cutoff_date >= auto_close_date:
                    # Close the survey
                    survey.status = SurveyStatus.CLOSED
                    survey.closed_at = datetime.utcnow()
                    self.session.add(survey)
                    closed_count += 1
                    
                    logger.info(f"Auto-closed survey {survey.id}")
        
        # Commit changes
        self.session.commit()
        
        logger.info(f"Auto-closed {closed_count} surveys")
        
        return {
            "closed_count": closed_count,
            "message": f"Auto-closed {closed_count} expired surveys"
        }
    
    def get_survey_completion_stats(self, survey_id: int) -> Dict[str, Any]:
        """Get completion statistics for a survey."""
        # Get all invitations
        query = select(SurveyInvitation).where(SurveyInvitation.survey_id == survey_id)
        invitations = self.session.exec(query).all()
        
        total_invitations = len(invitations)
        completed = len([i for i in invitations if i.completed_at])
        opened = len([i for i in invitations if i.opened_at])
        
        # Calculate response by day
        responses_by_day = {}
        for invitation in invitations:
            if invitation.completed_at:
                date_key = invitation.completed_at.date().isoformat()
                responses_by_day[date_key] = responses_by_day.get(date_key, 0) + 1
        
        return {
            "total_invitations": total_invitations,
            "completed_responses": completed,
            "opened_invitations": opened,
            "response_rate": (completed / total_invitations * 100) if total_invitations > 0 else 0,
            "open_rate": (opened / total_invitations * 100) if total_invitations > 0 else 0,
            "responses_by_day": responses_by_day
        }
    
    async def duplicate_survey(self, survey_id: int, new_title: Optional[str] = None) -> Survey:
        """Create a duplicate of an existing survey."""
        # Get original survey
        original_survey = self.session.get(Survey, survey_id)
        if not original_survey:
            raise ValueError("Survey not found")
        
        # Create duplicate
        duplicate_survey = Survey(
            title=new_title or f"{original_survey.title} (Copy)",
            description=original_survey.description,
            survey_type=original_survey.survey_type,
            org_id=original_survey.org_id,
            criteria=original_survey.criteria.copy() if original_survey.criteria else {},
            anonymize_responses=original_survey.anonymize_responses,
            reminder_enabled=original_survey.reminder_enabled,
            reminder_days=original_survey.reminder_days,
            auto_close_days=original_survey.auto_close_days,
            status=SurveyStatus.DRAFT
        )
        
        self.session.add(duplicate_survey)
        self.session.commit()
        self.session.refresh(duplicate_survey)
        
        logger.info(
            "Survey duplicated",
            original_id=survey_id,
            duplicate_id=duplicate_survey.id
        )
        
        return duplicate_survey
