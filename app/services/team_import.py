"""Team import service for processing CSV/Excel files and member data."""
import csv
import io
from typing import List, Dict, Any
import pandas as pd
from email_validator import validate_email, EmailNotValidError
from sqlmodel import Session, select
import structlog

from ..models import User, UserRole, TeamMemberImport
from .email_service import EmailService


logger = structlog.get_logger()


class TeamImportService:
    """Service for importing team members."""
    
    def __init__(self, session: Session):
        self.session = session
        self.email_service = EmailService()
    
    async def parse_csv(self, content: bytes) -> List[TeamMemberImport]:
        """Parse CSV content and extract team members."""
        try:
            # Decode content
            csv_content = content.decode('utf-8')
            
            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            members = []
            
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 for header
                try:
                    # Extract and validate email
                    email = row.get('email', '').strip()
                    if not email:
                        logger.warning(f"Row {row_num}: Missing email")
                        continue
                    
                    # Validate email format
                    try:
                        validated_email = validate_email(email)
                        email = validated_email.email
                    except EmailNotValidError as e:
                        logger.warning(f"Row {row_num}: Invalid email {email} - {str(e)}")
                        continue
                    
                    # Create member object
                    member = TeamMemberImport(
                        email=email,
                        first_name=row.get('first_name', '').strip() or None,
                        last_name=row.get('last_name', '').strip() or None,
                        department=row.get('department', '').strip() or None,
                        position=row.get('position', '').strip() or None,
                        employee_id=row.get('employee_id', '').strip() or None,
                    )
                    
                    members.append(member)
                    
                except Exception as e:
                    logger.error(f"Error processing row {row_num}: {str(e)}")
                    continue
            
            logger.info(f"Parsed CSV file: {len(members)} valid members found")
            return members
            
        except UnicodeDecodeError:
            # Try different encoding
            try:
                csv_content = content.decode('iso-8859-1')
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                # Process again with different encoding
                return await self._process_csv_rows(csv_reader)
            except Exception as e:
                logger.error(f"Failed to decode CSV file: {str(e)}")
                raise ValueError(f"Unable to decode CSV file: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            raise ValueError(f"Error parsing CSV file: {str(e)}")
    
    async def _process_csv_rows(self, csv_reader) -> List[TeamMemberImport]:
        """Process CSV rows into TeamMemberImport objects."""
        members = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                email = row.get('email', '').strip()
                if not email:
                    continue
                
                try:
                    validated_email = validate_email(email)
                    email = validated_email.email
                except EmailNotValidError:
                    continue
                
                member = TeamMemberImport(
                    email=email,
                    first_name=row.get('first_name', '').strip() or None,
                    last_name=row.get('last_name', '').strip() or None,
                    department=row.get('department', '').strip() or None,
                    position=row.get('position', '').strip() or None,
                    employee_id=row.get('employee_id', '').strip() or None,
                )
                
                members.append(member)
                
            except Exception as e:
                logger.error(f"Error processing row {row_num}: {str(e)}")
                continue
        
        return members
    
    async def parse_excel(self, content: bytes) -> List[TeamMemberImport]:
        """Parse Excel content and extract team members."""
        try:
            # Read Excel file
            df = pd.read_excel(io.BytesIO(content))
            
            # Convert column names to lowercase for consistency
            df.columns = df.columns.str.lower().str.strip()
            
            members = []
            
            for index, row in df.iterrows():
                try:
                    # Extract and validate email
                    email = str(row.get('email', '')).strip()
                    if not email or email == 'nan':
                        logger.warning(f"Row {index + 2}: Missing email")
                        continue
                    
                    # Validate email format
                    try:
                        validated_email = validate_email(email)
                        email = validated_email.email
                    except EmailNotValidError as e:
                        logger.warning(f"Row {index + 2}: Invalid email {email} - {str(e)}")
                        continue
                    
                    # Create member object
                    member = TeamMemberImport(
                        email=email,
                        first_name=self._safe_str(row.get('first_name')),
                        last_name=self._safe_str(row.get('last_name')),
                        department=self._safe_str(row.get('department')),
                        position=self._safe_str(row.get('position')),
                        employee_id=self._safe_str(row.get('employee_id')),
                    )
                    
                    members.append(member)
                    
                except Exception as e:
                    logger.error(f"Error processing row {index + 2}: {str(e)}")
                    continue
            
            logger.info(f"Parsed Excel file: {len(members)} valid members found")
            return members
            
        except Exception as e:
            logger.error(f"Error parsing Excel file: {str(e)}")
            raise ValueError(f"Error parsing Excel file: {str(e)}")
    
    def _safe_str(self, value) -> str | None:
        """Safely convert value to string, handling NaN and None."""
        if value is None or str(value).lower() in ['nan', 'none', '']:
            return None
        return str(value).strip()
    
    async def import_members(
        self,
        org_id: int,
        members: List[TeamMemberImport],
        send_invitations: bool = True
    ) -> Dict[str, Any]:
        """Import team members and optionally send invitations."""
        successful = 0
        failed = 0
        errors = []
        created_users = []
        
        for member in members:
            try:
                # Check if user already exists
                statement = select(User).where(User.email == member.email)
                existing_user = self.session.exec(statement).first()
                
                if existing_user:
                    if existing_user.org_id == org_id:
                        # User already in this organization
                        logger.warning(f"User {member.email} already exists in organization {org_id}")
                        errors.append({
                            "email": member.email,
                            "error": "User already exists in organization"
                        })
                        failed += 1
                        continue
                    else:
                        # User exists in different organization
                        logger.warning(f"User {member.email} exists in different organization")
                        errors.append({
                            "email": member.email,
                            "error": "User already exists in different organization"
                        })
                        failed += 1
                        continue
                
                # Create new user
                user = User(
                    email=member.email,
                    first_name=member.first_name,
                    last_name=member.last_name,
                    department=member.department,
                    position=member.position,
                    employee_id=member.employee_id,
                    role=UserRole.RESPONDENT,
                    org_id=org_id,
                    is_active=True,
                    is_verified=False,  # Will be verified when they complete first survey
                )
                
                self.session.add(user)
                self.session.commit()
                self.session.refresh(user)
                
                created_users.append(user)
                successful += 1
                
                logger.info(f"Created user {member.email} in organization {org_id}")
                
            except Exception as e:
                logger.error(f"Failed to create user {member.email}: {str(e)}")
                errors.append({
                    "email": member.email,
                    "error": str(e)
                })
                failed += 1
                continue
        
        # Send invitation emails if requested
        if send_invitations and created_users:
            try:
                await self._send_welcome_emails(created_users)
                logger.info(f"Sent welcome emails to {len(created_users)} users")
            except Exception as e:
                logger.error(f"Failed to send welcome emails: {str(e)}")
                # Don't fail the import if emails fail, just log the error
        
        return {
            "successful": successful,
            "failed": failed,
            "errors": errors,
            "created_users": len(created_users)
        }
    
    async def _send_welcome_emails(self, users: List[User]):
        """Send welcome emails to newly created users."""
        for user in users:
            try:
                await self.email_service.send_welcome_email(
                    to_email=user.email,
                    first_name=user.first_name,
                    organization_name="Your Organization"  # TODO: Get actual org name
                )
            except Exception as e:
                logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
                # Continue with other users even if one fails
                continue
    
    def validate_import_data(self, members: List[TeamMemberImport]) -> Dict[str, Any]:
        """Validate import data before processing."""
        errors = []
        warnings = []
        
        # Check for duplicates within the import
        emails = [member.email for member in members]
        duplicates = set([email for email in emails if emails.count(email) > 1])
        
        if duplicates:
            for email in duplicates:
                errors.append({
                    "email": email,
                    "error": "Duplicate email in import data"
                })
        
        # Validate email formats
        for member in members:
            try:
                validate_email(member.email)
            except EmailNotValidError as e:
                errors.append({
                    "email": member.email,
                    "error": f"Invalid email format: {str(e)}"
                })
        
        # Check for missing names
        for member in members:
            if not member.first_name and not member.last_name:
                warnings.append({
                    "email": member.email,
                    "warning": "Missing first and last name"
                })
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "total_members": len(members),
            "unique_emails": len(set(emails))
        }
