"""Scheduler service for automated tasks using APScheduler."""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select
import structlog

from ..database import get_session
from ..models import Survey, SurveyStatus, SurveyInvitation, AnalyticsSnapshot
from ..config import settings


logger = structlog.get_logger()

# Global scheduler instance
scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)


class SchedulerService:
    """Service for managing scheduled tasks."""
    
    def __init__(self):
        self.scheduler = scheduler
    
    async def send_survey_reminders(self):
        """Send reminder emails for incomplete surveys."""
        logger.info("Running survey reminders task")
        
        try:
            # Create a new session for this task
            session = next(get_session())
            
            # Get active surveys with reminders enabled
            active_surveys = session.exec(
                select(Survey).where(
                    Survey.status == SurveyStatus.ACTIVE,
                    Survey.reminder_enabled == True
                )
            ).all()
            
            from ..services.survey_service import SurveyService
            
            total_sent = 0
            total_failed = 0
            
            for survey in active_surveys:
                try:
                    survey_service = SurveyService(session)
                    result = await survey_service.send_survey_reminders(survey.id)
                    
                    total_sent += result.get('sent', 0)
                    total_failed += result.get('failed', 0)
                    
                    logger.info(
                        "Survey reminders processed",
                        survey_id=survey.id,
                        sent=result.get('sent', 0),
                        failed=result.get('failed', 0)
                    )
                    
                except Exception as e:
                    logger.error(
                        "Failed to send reminders for survey",
                        survey_id=survey.id,
                        error=str(e)
                    )
                    total_failed += 1
            
            logger.info(
                "Survey reminders task completed",
                total_sent=total_sent,
                total_failed=total_failed,
                surveys_processed=len(active_surveys)
            )
            
        except Exception as e:
            logger.error("Survey reminders task failed", error=str(e))
        finally:
            session.close()
    
    async def auto_close_expired_surveys(self):
        """Automatically close surveys that have reached their auto-close date."""
        logger.info("Running auto-close expired surveys task")
        
        try:
            session = next(get_session())
            
            from ..services.survey_service import SurveyService
            survey_service = SurveyService(session)
            
            result = await survey_service.auto_close_expired_surveys()
            
            logger.info(
                "Auto-close surveys task completed",
                closed_count=result.get('closed_count', 0)
            )
            
        except Exception as e:
            logger.error("Auto-close surveys task failed", error=str(e))
        finally:
            session.close()
    
    async def cleanup_expired_tokens(self):
        """Clean up expired survey invitation tokens."""
        logger.info("Running cleanup expired tokens task")
        
        try:
            session = next(get_session())
            
            # Get expired invitations
            expired_invitations = session.exec(
                select(SurveyInvitation).where(
                    SurveyInvitation.expires_at < datetime.utcnow(),
                    SurveyInvitation.completed_at.is_(None)
                )
            ).all()
            
            # Mark them as expired or delete them
            for invitation in expired_invitations:
                session.delete(invitation)
            
            session.commit()
            
            logger.info(
                "Cleanup expired tokens task completed",
                cleaned_up=len(expired_invitations)
            )
            
        except Exception as e:
            logger.error("Cleanup expired tokens task failed", error=str(e))
        finally:
            session.close()
    
    async def cleanup_old_analytics_snapshots(self):
        """Clean up old analytics snapshots."""
        logger.info("Running cleanup old analytics snapshots task")
        
        try:
            session = next(get_session())
            
            # Delete snapshots older than 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            old_snapshots = session.exec(
                select(AnalyticsSnapshot).where(
                    AnalyticsSnapshot.created_at < cutoff_date
                )
            ).all()
            
            for snapshot in old_snapshots:
                session.delete(snapshot)
            
            session.commit()
            
            logger.info(
                "Cleanup analytics snapshots task completed",
                cleaned_up=len(old_snapshots)
            )
            
        except Exception as e:
            logger.error("Cleanup analytics snapshots task failed", error=str(e))
        finally:
            session.close()
    
    async def generate_daily_reports(self):
        """Generate daily platform reports."""
        logger.info("Running daily reports generation task")
        
        try:
            session = next(get_session())
            
            # Calculate daily metrics
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            start_of_day = datetime.combine(yesterday, datetime.min.time())
            end_of_day = datetime.combine(yesterday, datetime.max.time())
            
            # Count new registrations
            from ..models import User, UserRole
            new_admins = session.exec(
                select(User).where(
                    User.role == UserRole.CLIENTADMIN,
                    User.created_at >= start_of_day,
                    User.created_at <= end_of_day
                )
            ).all()
            
            # Count new surveys
            new_surveys = session.exec(
                select(Survey).where(
                    Survey.created_at >= start_of_day,
                    Survey.created_at <= end_of_day
                )
            ).all()
            
            # Count responses
            from ..models import Response
            new_responses = session.exec(
                select(Response).where(
                    Response.submitted_at >= start_of_day,
                    Response.submitted_at <= end_of_day
                )
            ).all()
            
            # Count payments
            from ..models import Payment, PaymentStatus
            new_payments = session.exec(
                select(Payment).where(
                    Payment.status == PaymentStatus.COMPLETED,
                    Payment.paid_at >= start_of_day,
                    Payment.paid_at <= end_of_day
                )
            ).all()
            
            total_revenue = sum(p.amount_cents for p in new_payments) / 100
            
            # Log daily summary
            logger.info(
                "Daily report generated",
                date=yesterday.isoformat(),
                new_admins=len(new_admins),
                new_surveys=len(new_surveys),
                new_responses=len(new_responses),
                new_payments=len(new_payments),
                total_revenue_eur=total_revenue
            )
            
            # TODO: Send report email to admins if needed
            
        except Exception as e:
            logger.error("Daily reports generation task failed", error=str(e))
        finally:
            session.close()
    
    async def health_check_task(self):
        """Perform system health checks."""
        logger.info("Running system health check task")
        
        try:
            session = next(get_session())
            
            # Check database connectivity
            test_query = session.exec(select(Survey).limit(1)).first()
            
            # Check disk space
            import psutil
            disk_usage = psutil.disk_usage('/')
            disk_usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_usage_percent = memory.percent
            
            # Log health status
            logger.info(
                "System health check completed",
                database_status="healthy",
                disk_usage_percent=round(disk_usage_percent, 2),
                memory_usage_percent=round(memory_usage_percent, 2)
            )
            
            # Alert if resources are high
            if disk_usage_percent > 85:
                logger.warning("High disk usage detected", usage_percent=disk_usage_percent)
            
            if memory_usage_percent > 85:
                logger.warning("High memory usage detected", usage_percent=memory_usage_percent)
            
        except Exception as e:
            logger.error("System health check failed", error=str(e))
        finally:
            session.close()
    
    async def process_scheduled_surveys(self):
        """Process surveys that are scheduled to be activated."""
        logger.info("Running process scheduled surveys task")
        
        try:
            session = next(get_session())
            
            # Get surveys scheduled to start now or in the past
            scheduled_surveys = session.exec(
                select(Survey).where(
                    Survey.status == SurveyStatus.SCHEDULED,
                    Survey.scheduled_at <= datetime.utcnow()
                )
            ).all()
            
            from ..services.survey_service import SurveyService
            
            activated_count = 0
            failed_count = 0
            
            for survey in scheduled_surveys:
                try:
                    # Activate survey
                    survey.status = SurveyStatus.ACTIVE
                    survey.activated_at = datetime.utcnow()
                    session.add(survey)
                    
                    # Send invitations
                    survey_service = SurveyService(session)
                    await survey_service.send_survey_invitations(survey.id)
                    
                    activated_count += 1
                    
                    logger.info(
                        "Scheduled survey activated",
                        survey_id=survey.id,
                        title=survey.title
                    )
                    
                except Exception as e:
                    logger.error(
                        "Failed to activate scheduled survey",
                        survey_id=survey.id,
                        error=str(e)
                    )
                    failed_count += 1
            
            session.commit()
            
            logger.info(
                "Process scheduled surveys task completed",
                activated_count=activated_count,
                failed_count=failed_count
            )
            
        except Exception as e:
            logger.error("Process scheduled surveys task failed", error=str(e))
        finally:
            session.close()


def setup_scheduled_jobs():
    """Set up all scheduled jobs."""
    service = SchedulerService()
    
    # Survey reminders - every 2 hours during business hours
    scheduler.add_job(
        service.send_survey_reminders,
        CronTrigger(hour="9-17/2", minute=0),  # 9 AM, 11 AM, 1 PM, 3 PM, 5 PM
        id="survey_reminders",
        name="Send Survey Reminders",
        replace_existing=True,
        misfire_grace_time=300  # 5 minutes grace time
    )
    
    # Auto-close expired surveys - daily at 2 AM
    scheduler.add_job(
        service.auto_close_expired_surveys,
        CronTrigger(hour=2, minute=0),
        id="auto_close_surveys",
        name="Auto Close Expired Surveys",
        replace_existing=True
    )
    
    # Process scheduled surveys - every 15 minutes
    scheduler.add_job(
        service.process_scheduled_surveys,
        IntervalTrigger(minutes=15),
        id="process_scheduled_surveys",
        name="Process Scheduled Surveys",
        replace_existing=True
    )
    
    # Cleanup expired tokens - daily at 3 AM
    scheduler.add_job(
        service.cleanup_expired_tokens,
        CronTrigger(hour=3, minute=0),
        id="cleanup_expired_tokens",
        name="Cleanup Expired Tokens",
        replace_existing=True
    )
    
    # Cleanup old analytics snapshots - weekly on Sunday at 4 AM
    scheduler.add_job(
        service.cleanup_old_analytics_snapshots,
        CronTrigger(day_of_week="sun", hour=4, minute=0),
        id="cleanup_analytics_snapshots",
        name="Cleanup Old Analytics Snapshots",
        replace_existing=True
    )
    
    # Generate daily reports - daily at 6 AM
    scheduler.add_job(
        service.generate_daily_reports,
        CronTrigger(hour=6, minute=0),
        id="daily_reports",
        name="Generate Daily Reports",
        replace_existing=True
    )
    
    # System health check - every hour
    scheduler.add_job(
        service.health_check_task,
        IntervalTrigger(hours=1),
        id="health_check",
        name="System Health Check",
        replace_existing=True
    )
    
    logger.info("Scheduled jobs configured")


# Initialize jobs when module is imported
if not scheduler.running:
    setup_scheduled_jobs()


# Scheduler management functions
def start_scheduler():
    """Start the scheduler."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.info("Scheduler already running")


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
    else:
        logger.info("Scheduler not running")


def get_scheduler_status() -> Dict[str, Any]:
    """Get scheduler status and job information."""
    jobs = []
    
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
            "misfire_grace_time": job.misfire_grace_time
        })
    
    return {
        "running": scheduler.running,
        "timezone": str(scheduler.timezone),
        "job_count": len(jobs),
        "jobs": jobs
    }


async def run_job_manually(job_id: str) -> Dict[str, Any]:
    """Manually trigger a scheduled job."""
    try:
        job = scheduler.get_job(job_id)
        if not job:
            return {"success": False, "error": f"Job {job_id} not found"}
        
        # Run the job
        await job.func()
        
        logger.info("Manual job execution completed", job_id=job_id)
        
        return {
            "success": True,
            "job_id": job_id,
            "job_name": job.name,
            "executed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Manual job execution failed", job_id=job_id, error=str(e))
        return {
            "success": False,
            "job_id": job_id,
            "error": str(e)
        }
