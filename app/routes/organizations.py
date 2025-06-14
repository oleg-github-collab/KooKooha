"""Organization management routes."""
import csv
import io
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr, validator
import structlog

from ..database import get_session
from ..models import (
    User, UserCreate, UserRead, UserRole,
    Organization, OrganizationRead, OrganizationUpdate,
    TeamImport, TeamImportCreate, TeamImportRead
)
from ..auth import get_current_user, verify_organization_access, require_client_admin
from ..services.email_service import EmailService
from ..services.team_import import TeamImportService
from ..config import settings


logger = structlog.get_logger()
router = APIRouter()


class TeamMemberImport(BaseModel):
    """Team member import model."""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    employee_id: Optional[str] = None


class TeamImportRequest(BaseModel):
    """Team import request model."""
    members: List[TeamMemberImport]
    send_invitations: bool = True


class TeamImportResponse(BaseModel):
    """Team import response model."""
    import_id: int
    total_members: int
    successful_imports: int
    failed_imports: int
    errors: Optional[List[Dict[str, Any]]] = None
    message: str


class OrganizationStats(BaseModel):
    """Organization statistics model."""
    total_members: int
    active_surveys: int
    completed_surveys: int
    response_rate: float
    last_survey_date: Optional[datetime]


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_organization(
    org_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(verify_organization_access)
):
    """Get organization details."""
    statement = select(Organization).where(Organization.id == org_id)
    organization = session.exec(statement).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return OrganizationRead.model_validate(organization)


@router.put("/{org_id}", response_model=OrganizationRead)
async def update_organization(
    org_id: int,
    update_data: OrganizationUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(verify_organization_access)
):
    """Update organization details."""
    # Only client admin or superadmin can update
    if current_user.role not in [UserRole.CLIENTADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    statement = select(Organization).where(Organization.id == org_id)
    organization = session.exec(statement).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(organization, field, value)
    
    organization.updated_at = datetime.utcnow()
    session.add(organization)
    session.commit()
    session.refresh(organization)
    
    logger.info("Organization updated", org_id=org_id, updated_by=current_user.id)
    
    return OrganizationRead.model_validate(organization)


@router.get("/{org_id}/members", response_model=List[UserRead])
async def get_organization_members(
    org_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(verify_organization_access)
):
    """Get all organization members."""
    statement = select(User).where(
        User.org_id == org_id,
        User.is_active == True
    ).order_by(User.email)
    
    members = session.exec(statement).all()
    return [UserRead.model_validate(member) for member in members]


@router.post("/{org_id}/team/import", response_model=TeamImportResponse)
async def import_team_members(
    org_id: int,
    import_data: TeamImportRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_client_admin)
):
    """Import team members from JSON data."""
    # Verify organization access
    await verify_organization_access(org_id, current_user)
    
    logger.info(
        "Starting team import",
        org_id=org_id,
        member_count=len(import_data.members),
        user_id=current_user.id
    )
    
    # Create import record
    import_record = TeamImport(
        org_id=org_id,
        filename="json_import",
        total_emails=len(import_data.members),
        processed_emails=0,
        failed_emails=0,
        status="processing"
    )
    session.add(import_record)
    session.commit()
    session.refresh(import_record)
    
    try:
        # Initialize team import service
        import_service = TeamImportService(session)
        
        # Process imports
        results = await import_service.import_members(
            org_id=org_id,
            members=import_data.members,
            send_invitations=import_data.send_invitations
        )
        
        # Update import record
        import_record.processed_emails = results["successful"]
        import_record.failed_emails = results["failed"]
        import_record.status = "completed"
        import_record.errors = results.get("errors", [])
        
        session.add(import_record)
        session.commit()
        
        logger.info(
            "Team import completed",
            import_id=import_record.id,
            successful=results["successful"],
            failed=results["failed"]
        )
        
        return TeamImportResponse(
            import_id=import_record.id,
            total_members=len(import_data.members),
            successful_imports=results["successful"],
            failed_imports=results["failed"],
            errors=results.get("errors", []),
            message=f"Import completed. {results['successful']} successful, {results['failed']} failed."
        )
        
    except Exception as e:
        # Update import record with error
        import_record.status = "failed"
        import_record.errors = [{"error": str(e)}]
        session.add(import_record)
        session.commit()
        
        logger.error("Team import failed", import_id=import_record.id, error=str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.post("/{org_id}/team/import/file", response_model=TeamImportResponse)
async def import_team_from_file(
    org_id: int,
    file: UploadFile = File(...),
    send_invitations: bool = Form(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_client_admin)
):
    """Import team members from CSV or Excel file."""
    # Verify organization access
    await verify_organization_access(org_id, current_user)
    
    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in ['csv', 'xlsx', 'xls']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV and Excel files are supported"
        )
    
    # Check file size
    content = await file.read()
    if len(content) > settings.upload_max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.upload_max_size} bytes"
        )
    
    logger.info(
        "Starting file import",
        org_id=org_id,
        filename=file.filename,
        file_size=len(content),
        user_id=current_user.id
    )
    
    # Create import record
    import_record = TeamImport(
        org_id=org_id,
        filename=file.filename,
        total_emails=0,  # Will be updated after parsing
        processed_emails=0,
        failed_emails=0,
        status="processing"
    )
    session.add(import_record)
    session.commit()
    session.refresh(import_record)
    
    try:
        # Initialize import service
        import_service = TeamImportService(session)
        
        # Parse file and import members
        if file_extension == 'csv':
            members = await import_service.parse_csv(content)
        else:
            members = await import_service.parse_excel(content)
        
        # Update total count
        import_record.total_emails = len(members)
        session.add(import_record)
        session.commit()
        
        # Process imports
        results = await import_service.import_members(
            org_id=org_id,
            members=members,
            send_invitations=send_invitations
        )
        
        # Update import record
        import_record.processed_emails = results["successful"]
        import_record.failed_emails = results["failed"]
        import_record.status = "completed"
        import_record.errors = results.get("errors", [])
        
        session.add(import_record)
        session.commit()
        
        logger.info(
            "File import completed",
            import_id=import_record.id,
            successful=results["successful"],
            failed=results["failed"]
        )
        
        return TeamImportResponse(
            import_id=import_record.id,
            total_members=len(members),
            successful_imports=results["successful"],
            failed_imports=results["failed"],
            errors=results.get("errors", []),
            message=f"Import completed. {results['successful']} successful, {results['failed']} failed."
        )
        
    except Exception as e:
        # Update import record with error
        import_record.status = "failed"
        import_record.errors = [{"error": str(e)}]
        session.add(import_record)
        session.commit()
        
        logger.error("File import failed", import_id=import_record.id, error=str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.get("/{org_id}/team/imports", response_model=List[TeamImportRead])
async def get_team_imports(
    org_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(verify_organization_access)
):
    """Get team import history."""
    statement = select(TeamImport).where(
        TeamImport.org_id == org_id
    ).order_by(TeamImport.created_at.desc())
    
    imports = session.exec(statement).all()
    return [TeamImportRead.model_validate(import_record) for import_record in imports]


@router.get("/{org_id}/team/imports/{import_id}", response_model=TeamImportRead)
async def get_team_import(
    org_id: int,
    import_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(verify_organization_access)
):
    """Get specific team import details."""
    statement = select(TeamImport).where(
        TeamImport.id == import_id,
        TeamImport.org_id == org_id
    )
    
    import_record = session.exec(statement).first()
    if not import_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import record not found"
        )
    
    return TeamImportRead.model_validate(import_record)


@router.delete("/{org_id}/members/{member_id}")
async def remove_team_member(
    org_id: int,
    member_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_client_admin)
):
    """Remove team member from organization."""
    # Verify organization access
    await verify_organization_access(org_id, current_user)
    
    statement = select(User).where(
        User.id == member_id,
        User.org_id == org_id,
        User.role == UserRole.RESPONDENT
    )
    
    member = session.exec(statement).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
    
    # Don't allow deletion of admin users through this endpoint
    if member.role in [UserRole.CLIENTADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot remove admin users through this endpoint"
        )
    
    # Soft delete by marking as inactive
    member.is_active = False
    member.updated_at = datetime.utcnow()
    session.add(member)
    session.commit()
    
    logger.info(
        "Team member removed",
        org_id=org_id,
        member_id=member_id,
        removed_by=current_user.id
    )
    
    return {"message": "Team member removed successfully"}


@router.get("/{org_id}/stats", response_model=OrganizationStats)
async def get_organization_stats(
    org_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(verify_organization_access)
):
    """Get organization statistics."""
    # Count total members
    total_members_stmt = select(User).where(
        User.org_id == org_id,
        User.is_active == True,
        User.role == UserRole.RESPONDENT
    )
    total_members = len(session.exec(total_members_stmt).all())
    
    # Count surveys (will be implemented when surveys routes are ready)
    active_surveys = 0
    completed_surveys = 0
    response_rate = 0.0
    last_survey_date = None
    
    # Placeholder until survey statistics are implemented
    
    return OrganizationStats(
        total_members=total_members,
        active_surveys=active_surveys,
        completed_surveys=completed_surveys,
        response_rate=response_rate,
        last_survey_date=last_survey_date
    )


@router.get("/{org_id}/members/download")
async def download_team_members(
    org_id: int,
    format: str = "csv",
    session: Session = Depends(get_session),
    current_user: User = Depends(verify_organization_access)
):
    """Download team members list."""
    if format not in ["csv", "json"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'csv' or 'json'"
        )
    
    statement = select(User).where(
        User.org_id == org_id,
        User.is_active == True,
        User.role == UserRole.RESPONDENT
    ).order_by(User.email)
    
    members = session.exec(statement).all()
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "email", "first_name", "last_name", "department", 
            "position", "employee_id", "created_at"
        ])
        
        # Write data
        for member in members:
            writer.writerow([
                member.email,
                member.first_name or "",
                member.last_name or "",
                member.department or "",
                member.position or "",
                member.employee_id or "",
                member.created_at.isoformat() if member.created_at else ""
            ])
        
        from fastapi.responses import StreamingResponse
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=team_members_{org_id}.csv"}
        )
    
    else:  # JSON format
        members_data = []
        for member in members:
            members_data.append({
                "email": member.email,
                "first_name": member.first_name,
                "last_name": member.last_name,
                "department": member.department,
                "position": member.position,
                "employee_id": member.employee_id,
                "created_at": member.created_at.isoformat() if member.created_at else None
            })
        
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content={"members": members_data},
            headers={"Content-Disposition": f"attachment; filename=team_members_{org_id}.json"}
        )
