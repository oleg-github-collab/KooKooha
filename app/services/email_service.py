"""Email service using SendGrid API."""
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent, HtmlContent
from jinja2 import Environment, BaseLoader
import structlog

from ..config import settings


logger = structlog.get_logger()


class TemplateLoader(BaseLoader):
    """Custom template loader for email templates."""
    
    def __init__(self):
        self.templates = {
            'welcome': {
                'subject': 'Welcome to {{ organization_name }} - Human Lens Survey Platform',
                'text': '''
Hello {{ first_name or 'Team Member' }},

Welcome to {{ organization_name }}!

You have been added to our Human Lens survey platform. You will receive an email with a survey link when new assessments are available.

If you have any questions, please contact your HR team or administrator.

Best regards,
The Kookooha Team
''',
                'html': '''
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #6366f1;">Kookooha</h1>
            <p style="color: #666;">Mental Health & Corporate Culture</p>
        </div>
        
        <h2>Welcome to {{ organization_name }}!</h2>
        
        <p>Hello {{ first_name or 'Team Member' }},</p>
        
        <p>You have been added to our Human Lens survey platform. This platform helps organizations create mentally healthy workplaces through data-driven insights.</p>
        
        <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #6366f1;">What to expect:</h3>
            <ul>
                <li>You will receive survey invitations via email</li>
                <li>Each survey takes 5-10 minutes to complete</li>
                <li>Your responses are confidential and anonymized</li>
                <li>Results help improve workplace culture and wellbeing</li>
            </ul>
        </div>
        
        <p>If you have any questions, please contact your HR team or administrator.</p>
        
        <p>Best regards,<br>The Kookooha Team</p>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
        <p style="font-size: 12px; color: #666; text-align: center;">
            This email was sent by Kookooha on behalf of {{ organization_name }}
        </p>
    </div>
</body>
</html>
'''
            },
            'survey_invitation': {
                'subject': 'New Survey Available - {{ survey_title }}',
                'text': '''
Hello {{ first_name or 'Team Member' }},

A new survey is available for you to complete: {{ survey_title }}

{{ survey_description }}

To participate, please click the link below:
{{ survey_link }}

This survey will take approximately {{ estimated_time or '5-10' }} minutes to complete.
Your responses are confidential and will be used to improve workplace culture.

The survey will be available until {{ expires_at.strftime('%B %d, %Y') if expires_at else 'further notice' }}.

If you have any questions, please contact your administrator.

Best regards,
The Kookooha Team
''',
                'html': '''
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #6366f1;">Kookooha</h1>
            <p style="color: #666;">Mental Health & Corporate Culture</p>
        </div>
        
        <h2>New Survey Available</h2>
        
        <p>Hello {{ first_name or 'Team Member' }},</p>
        
        <p>A new survey is available for you to complete:</p>
        
        <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #6366f1;">{{ survey_title }}</h3>
            {% if survey_description %}
            <p>{{ survey_description }}</p>
            {% endif %}
            <p><strong>Estimated time:</strong> {{ estimated_time or '5-10' }} minutes</p>
            {% if expires_at %}
            <p><strong>Available until:</strong> {{ expires_at.strftime('%B %d, %Y') }}</p>
            {% endif %}
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ survey_link }}" 
               style="background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                Start Survey
            </a>
        </div>
        
        <div style="background: #ecfdf5; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0; font-size: 14px; color: #065f46;">
                🔒 Your responses are confidential and will be anonymized for analysis.
            </p>
        </div>
        
        <p>If you have any questions, please contact your administrator.</p>
        
        <p>Best regards,<br>The Kookooha Team</p>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
        <p style="font-size: 12px; color: #666; text-align: center;">
            This email was sent by Kookooha. If you no longer wish to receive survey invitations, please contact your administrator.
        </p>
    </div>
</body>
</html>
'''
            },
            'survey_reminder': {
                'subject': 'Reminder: {{ survey_title }} - Response Needed',
                'text': '''
Hello {{ first_name or 'Team Member' }},

This is a friendly reminder that you have a pending survey to complete: {{ survey_title }}

{{ survey_description }}

To participate, please click the link below:
{{ survey_link }}

This survey will take approximately {{ estimated_time or '5-10' }} minutes to complete.

The survey will close on {{ expires_at.strftime('%B %d, %Y') if expires_at else 'soon' }}.

Your participation is important for improving our workplace culture.

Best regards,
The Kookooha Team
''',
                'html': '''
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #6366f1;">Kookooha</h1>
            <p style="color: #666;">Mental Health & Corporate Culture</p>
        </div>
        
        <h2 style="color: #dc2626;">⏰ Survey Reminder</h2>
        
        <p>Hello {{ first_name or 'Team Member' }},</p>
        
        <p>This is a friendly reminder that you have a pending survey to complete:</p>
        
        <div style="background: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b;">
            <h3 style="margin-top: 0; color: #92400e;">{{ survey_title }}</h3>
            {% if survey_description %}
            <p>{{ survey_description }}</p>
            {% endif %}
            <p><strong>Estimated time:</strong> {{ estimated_time or '5-10' }} minutes</p>
            {% if expires_at %}
            <p><strong>Closes on:</strong> {{ expires_at.strftime('%B %d, %Y') }}</p>
            {% endif %}
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ survey_link }}" 
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
'''
            }
        }
    
    def get_source(self, environment, template):
        """Get template source."""
        if template not in self.templates:
            raise ValueError(f"Template '{template}' not found")
        
        template_data = self.templates[template]
        return template_data, None, lambda: True


class EmailService:
    """Email service for sending notifications via SendGrid."""
    
    def __init__(self):
        self.sg = SendGridAPIClient(api_key=settings.sendgrid_api_key)
        self.jinja_env = Environment(loader=TemplateLoader())
        self.from_email = From(settings.from_email, settings.from_name)
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        text_content: str,
        html_content: Optional[str] = None,
        to_name: Optional[str] = None
    ) -> bool:
        """Send an email via SendGrid."""
        try:
            # Create the mail object
            to = To(to_email, to_name)
            
            mail = Mail(
                from_email=self.from_email,
                to_emails=to,
                subject=Subject(subject),
                plain_text_content=PlainTextContent(text_content)
            )
            
            if html_content:
                mail.content = [
                    PlainTextContent(text_content),
                    HtmlContent(html_content)
                ]
            
            # Send the email
            response = self.sg.send(mail)
            
            if response.status_code in [200, 202]:
                logger.info(
                    "Email sent successfully",
                    to_email=to_email,
                    subject=subject,
                    status_code=response.status_code
                )
                return True
            else:
                logger.error(
                    "Failed to send email",
                    to_email=to_email,
                    subject=subject,
                    status_code=response.status_code,
                    body=response.body
                )
                return False
                
        except Exception as e:
            logger.error(
                "Error sending email",
                to_email=to_email,
                subject=subject,
                error=str(e)
            )
            return False
    
    async def send_template_email(
        self,
        to_email: str,
        template_name: str,
        template_data: Dict[str, Any],
        to_name: Optional[str] = None
    ) -> bool:
        """Send an email using a template."""
        try:
            # Get templates
            subject_template = self.jinja_env.get_template(template_name)
            text_template = self.jinja_env.get_template(template_name)
            html_template = self.jinja_env.get_template(template_name)
            
            # Render templates
            subject = subject_template.get_template('subject').render(**template_data)
            text_content = text_template.get_template('text').render(**template_data)
            html_content = html_template.get_template('html').render(**template_data)
            
            # Send email
            return await self.send_email(
                to_email=to_email,
                subject=subject,
                text_content=text_content,
                html_content=html_content,
                to_name=to_name
            )
            
        except Exception as e:
            logger.error(
                "Error sending template email",
                to_email=to_email,
                template_name=template_name,
                error=str(e)
            )
            return False
    
    async def send_welcome_email(
        self,
        to_email: str,
        first_name: Optional[str] = None,
        organization_name: str = "Your Organization"
    ) -> bool:
        """Send welcome email to new team member."""
        template_data = {
            'first_name': first_name,
            'organization_name': organization_name,
        }
        
        # Manual template rendering for welcome email
        subject = f"Welcome to {organization_name} - Human Lens Survey Platform"
        
        text_content = f"""
Hello {first_name or 'Team Member'},

Welcome to {organization_name}!

You have been added to our Human Lens survey platform. You will receive an email with a survey link when new assessments are available.

If you have any questions, please contact your HR team or administrator.

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
        
        <h2>Welcome to {organization_name}!</h2>
        
        <p>Hello {first_name or 'Team Member'},</p>
        
        <p>You have been added to our Human Lens survey platform. This platform helps organizations create mentally healthy workplaces through data-driven insights.</p>
        
        <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #6366f1;">What to expect:</h3>
            <ul>
                <li>You will receive survey invitations via email</li>
                <li>Each survey takes 5-10 minutes to complete</li>
                <li>Your responses are confidential and anonymized</li>
                <li>Results help improve workplace culture and wellbeing</li>
            </ul>
        </div>
        
        <p>If you have any questions, please contact your HR team or administrator.</p>
        
        <p>Best regards,<br>The Kookooha Team</p>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
        <p style="font-size: 12px; color: #666; text-align: center;">
            This email was sent by Kookooha on behalf of {organization_name}
        </p>
    </div>
</body>
</html>
"""
        
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            text_content=text_content,
            html_content=html_content,
            to_name=first_name
        )
    
    async def send_survey_invitation(
        self,
        to_email: str,
        survey_title: str,
        survey_link: str,
        first_name: Optional[str] = None,
        survey_description: Optional[str] = None,
        estimated_time: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """Send survey invitation email."""
        subject = f"New Survey Available - {survey_title}"
        
        text_content = f"""
Hello {first_name or 'Team Member'},

A new survey is available for you to complete: {survey_title}

{survey_description or ''}

To participate, please click the link below:
{survey_link}

This survey will take approximately {estimated_time or '5-10'} minutes to complete.
Your responses are confidential and will be used to improve workplace culture.

The survey will be available until {expires_at.strftime('%B %d, %Y') if expires_at else 'further notice'}.

If you have any questions, please contact your administrator.

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
        
        <h2>New Survey Available</h2>
        
        <p>Hello {first_name or 'Team Member'},</p>
        
        <p>A new survey is available for you to complete:</p>
        
        <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #6366f1;">{survey_title}</h3>
            {"<p>" + survey_description + "</p>" if survey_description else ""}
            <p><strong>Estimated time:</strong> {estimated_time or '5-10'} minutes</p>
            {"<p><strong>Available until:</strong> " + expires_at.strftime('%B %d, %Y') + "</p>" if expires_at else ""}
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{survey_link}" 
               style="background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                Start Survey
            </a>
        </div>
        
        <div style="background: #ecfdf5; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0; font-size: 14px; color: #065f46;">
                🔒 Your responses are confidential and will be anonymized for analysis.
            </p>
        </div>
        
        <p>If you have any questions, please contact your administrator.</p>
        
        <p>Best regards,<br>The Kookooha Team</p>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
        <p style="font-size: 12px; color: #666; text-align: center;">
            This email was sent by Kookooha. If you no longer wish to receive survey invitations, please contact your administrator.
        </p>
    </div>
</body>
</html>
"""
        
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            text_content=text_content,
            html_content=html_content,
            to_name=first_name
        )
    
    async def send_bulk_emails(
        self,
        recipients: List[Dict[str, Any]],
        template_name: str,
        template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send bulk emails to multiple recipients."""
        successful = 0
        failed = 0
        errors = []
        
        for recipient in recipients:
            try:
                # Merge recipient-specific data with template data
                recipient_data = {**template_data, **recipient}
                
                success = await self.send_template_email(
                    to_email=recipient['email'],
                    template_name=template_name,
                    template_data=recipient_data,
                    to_name=recipient.get('name')
                )
                
                if success:
                    successful += 1
                else:
                    failed += 1
                    errors.append({
                        'email': recipient['email'],
                        'error': 'Failed to send email'
                    })
                    
            except Exception as e:
                failed += 1
                errors.append({
                    'email': recipient.get('email', 'unknown'),
                    'error': str(e)
                })
        
        return {
            'successful': successful,
            'failed': failed,
            'errors': errors
        }