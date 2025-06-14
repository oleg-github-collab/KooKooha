"""Survey response routes."""
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select
from pydantic import BaseModel, validator
import structlog

from ..database import get_session
from ..models import (
    Response, ResponseCreate, ResponseRead,
    Survey, SurveyInvitation, User, SurveyStatus
)
from ..auth import verify_survey_token, get_current_user, verify_organization_access
from ..config import settings


logger = structlog.get_logger()
router = APIRouter()


class SurveyResponseRequest(BaseModel):
    """Survey response submission model."""
    token: str
    answers: Dict[str, Any]
    
    @validator('answers')
    def validate_answers(cls, v):
        if not v:
            raise ValueError('Answers cannot be empty')
        return v


class SurveyResponseSubmission(BaseModel):
    """Survey response submission without token (for authenticated users)."""
    answers: Dict[str, Any]
    
    @validator('answers')
    def validate_answers(cls, v):
        if not v:
            raise ValueError('Answers cannot be empty')
        return v


class ResponseAnalytics(BaseModel):
    """Response analytics model."""
    question_id: str
    question_text: str
    question_type: str
    responses: List[Any]
    summary_stats: Optional[Dict[str, Any]] = None


@router.post("/submit", response_model=Dict[str, Any])
async def submit_survey_response(
    response_data: SurveyResponseRequest,
    request: Request,
    session: Session = Depends(get_session)
):
    """Submit survey response using token (public endpoint)."""
    try:
        # Verify survey token
        payload = await verify_survey_token(response_data.token, session)
        survey_id = payload.get('survey_id')
        respondent_id = payload.get('respondent_id')
        invitation_id = payload.get('invitation_id')
        
        logger.info(
            "Survey response submission started",
            survey_id=survey_id,
            respondent_id=respondent_id,
            invitation_id=invitation_id
        )
        
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
        
        # Check for duplicate responses
        if respondent_id and invitation_id:
            existing_response = session.exec(
                select(Response).where(
                    Response.survey_id == survey_id,
                    Response.respondent_id == respondent_id
                )
            ).first()
            
            if existing_response:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Response already submitted for this survey"
                )
        
        # Validate answers against survey criteria
        validation_result = _validate_survey_answers(
            answers=response_data.answers,
            survey=survey
        )
        
        if not validation_result['is_valid']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid answers: {validation_result['errors']}"
            )
        
        # Create response
        response = Response(
            survey_id=survey_id,
            respondent_id=respondent_id,
            invitation_id=invitation_id,
            answers=response_data.answers,
            submitted_at=datetime.utcnow(),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        
        session.add(response)
        
        # Update invitation as completed
        if invitation_id:
            invitation = session.get(SurveyInvitation, invitation_id)
            if invitation:
                invitation.completed_at = datetime.utcnow()
                session.add(invitation)
        
        session.commit()
        session.refresh(response)
        
        logger.info(
            "Survey response submitted successfully",
            response_id=response.id,
            survey_id=survey_id,
            respondent_id=respondent_id
        )
        
        return {
            "message": "Response submitted successfully",
            "response_id": response.id,
            "survey_id": survey_id,
            "submitted_at": response.submitted_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to submit survey response", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit response"
        )


@router.post("/{survey_id}/submit", response_model=Dict[str, Any])
async def submit_authenticated_response(
    survey_id: int,
    response_data: SurveyResponseSubmission,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Submit survey response for authenticated user."""
    # Get survey
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
            detail="Survey is not currently active"
        )
    
    # Check for duplicate responses
    existing_response = session.exec(
        select(Response).where(
            Response.survey_id == survey_id,
            Response.respondent_id == current_user.id
        )
    ).first()
    
    if existing_response:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Response already submitted for this survey"
        )
    
    # Validate answers
    validation_result = _validate_survey_answers(
        answers=response_data.answers,
        survey=survey
    )
    
    if not validation_result['is_valid']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid answers: {validation_result['errors']}"
        )
    
    # Create response
    response = Response(
        survey_id=survey_id,
        respondent_id=current_user.id,
        answers=response_data.answers,
        submitted_at=datetime.utcnow(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get('user-agent')
    )
    
    session.add(response)
    session.commit()
    session.refresh(response)
    
    logger.info(
        "Authenticated survey response submitted",
        response_id=response.id,
        survey_id=survey_id,
        user_id=current_user.id
    )
    
    return {
        "message": "Response submitted successfully",
        "response_id": response.id,
        "survey_id": survey_id,
        "submitted_at": response.submitted_at
    }


@router.get("/{survey_id}", response_model=List[ResponseRead])
async def get_survey_responses(
    survey_id: int,
    include_personal_data: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all responses for a survey."""
    # Get survey
    survey = session.get(Survey, survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Verify organization access
    await verify_organization_access(survey.org_id, current_user)
    
    # Get responses
    query = select(Response).where(Response.survey_id == survey_id)
    responses = session.exec(query).all()
    
    # Filter out personal data if anonymization is enabled
    if survey.anonymize_responses and not include_personal_data:
        for response in responses:
            response.respondent_id = None
            response.ip_address = None
            response.user_agent = None
    
    return [ResponseRead.model_validate(response) for response in responses]


@router.get("/{survey_id}/analytics")
async def get_response_analytics(
    survey_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get analytics for survey responses."""
    # Get survey
    survey = session.get(Survey, survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Verify organization access
    await verify_organization_access(survey.org_id, current_user)
    
    # Get responses
    query = select(Response).where(Response.survey_id == survey_id)
    responses = session.exec(query).all()
    
    if not responses:
        return {
            "survey_id": survey_id,
            "total_responses": 0,
            "analytics": [],
            "summary": {}
        }
    
    # Analyze responses
    analytics = _analyze_responses(responses, survey)
    
    return {
        "survey_id": survey_id,
        "total_responses": len(responses),
        "analytics": analytics,
        "summary": _generate_response_summary(responses, survey)
    }


@router.get("/{survey_id}/export")
async def export_survey_responses(
    survey_id: int,
    format: str = "csv",
    include_personal_data: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Export survey responses."""
    if format not in ["csv", "json", "xlsx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'csv', 'json', or 'xlsx'"
        )
    
    # Get survey
    survey = session.get(Survey, survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Verify organization access
    await verify_organization_access(survey.org_id, current_user)
    
    # Get responses
    query = select(Response).where(Response.survey_id == survey_id)
    responses = session.exec(query).all()
    
    if not responses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No responses found"
        )
    
    # Export based on format
    if format == "csv":
        return _export_responses_csv(responses, survey, include_personal_data)
    elif format == "json":
        return _export_responses_json(responses, survey, include_personal_data)
    elif format == "xlsx":
        return _export_responses_xlsx(responses, survey, include_personal_data)


@router.delete("/{survey_id}/responses/{response_id}")
async def delete_response(
    survey_id: int,
    response_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete a specific response."""
    # Get survey
    survey = session.get(Survey, survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Verify organization access
    await verify_organization_access(survey.org_id, current_user)
    
    # Get response
    response = session.exec(
        select(Response).where(
            Response.id == response_id,
            Response.survey_id == survey_id
        )
    ).first()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Response not found"
        )
    
    # Delete response
    session.delete(response)
    session.commit()
    
    logger.info(
        "Survey response deleted",
        response_id=response_id,
        survey_id=survey_id,
        deleted_by=current_user.id
    )
    
    return {"message": "Response deleted successfully"}


# Helper functions

def _validate_survey_answers(answers: Dict[str, Any], survey: Survey) -> Dict[str, Any]:
    """Validate survey answers against survey criteria."""
    errors = []
    
    # Get expected questions from survey criteria
    expected_questions = survey.criteria.get('questions', [])
    
    if not expected_questions:
        # If no specific questions defined, accept any answers
        return {"is_valid": True, "errors": []}
    
    # Check required questions
    for question in expected_questions:
        question_id = question.get('id')
        required = question.get('required', False)
        
        if required and question_id not in answers:
            errors.append(f"Required question '{question_id}' not answered")
    
    # Validate answer formats
    for question_id, answer in answers.items():
        question_def = next(
            (q for q in expected_questions if q.get('id') == question_id),
            None
        )
        
        if question_def:
            question_type = question_def.get('type', 'text')
            
            # Validate based on question type
            if question_type == 'rating' and not isinstance(answer, (int, float)):
                errors.append(f"Question '{question_id}' must have numeric answer")
            elif question_type == 'choice' and answer not in question_def.get('options', []):
                errors.append(f"Question '{question_id}' has invalid choice")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors
    }


def _analyze_responses(responses: List[Response], survey: Survey) -> List[Dict[str, Any]]:
    """Analyze survey responses."""
    analytics = []
    
    # Get all unique question IDs
    all_questions = set()
    for response in responses:
        all_questions.update(response.answers.keys())
    
    # Analyze each question
    for question_id in all_questions:
        question_responses = []
        for response in responses:
            if question_id in response.answers:
                question_responses.append(response.answers[question_id])
        
        if question_responses:
            analytics.append({
                "question_id": question_id,
                "total_responses": len(question_responses),
                "response_rate": len(question_responses) / len(responses) * 100,
                "summary": _analyze_question_responses(question_responses)
            })
    
    return analytics


def _analyze_question_responses(responses: List[Any]) -> Dict[str, Any]:
    """Analyze responses for a specific question."""
    if not responses:
        return {}
    
    # Determine response type
    sample_response = responses[0]
    
    if isinstance(sample_response, (int, float)):
        # Numeric responses
        import statistics
        return {
            "type": "numeric",
            "count": len(responses),
            "mean": statistics.mean(responses),
            "median": statistics.median(responses),
            "min": min(responses),
            "max": max(responses),
            "std_dev": statistics.stdev(responses) if len(responses) > 1 else 0
        }
    
    elif isinstance(sample_response, str):
        # Text responses
        from collections import Counter
        counter = Counter(responses)
        return {
            "type": "text",
            "count": len(responses),
            "unique_responses": len(counter),
            "most_common": counter.most_common(5)
        }
    
    elif isinstance(sample_response, list):
        # Multi-choice responses
        from collections import Counter
        all_choices = []
        for response in responses:
            if isinstance(response, list):
                all_choices.extend(response)
        
        counter = Counter(all_choices)
        return {
            "type": "multi_choice",
            "count": len(responses),
            "total_choices": len(all_choices),
            "choice_distribution": dict(counter)
        }
    
    else:
        return {
            "type": "unknown",
            "count": len(responses)
        }


def _generate_response_summary(responses: List[Response], survey: Survey) -> Dict[str, Any]:
    """Generate overall response summary."""
    if not responses:
        return {}
    
    # Calculate completion time statistics
    completion_times = []
    for response in responses:
        if response.submitted_at and response.created_at:
            duration = (response.submitted_at - response.created_at).total_seconds() / 60
            completion_times.append(duration)
    
    import statistics
    
    summary = {
        "total_responses": len(responses),
        "survey_type": survey.survey_type,
        "response_period": {
            "start": min(r.submitted_at for r in responses).isoformat(),
            "end": max(r.submitted_at for r in responses).isoformat()
        }
    }
    
    if completion_times:
        summary["completion_time_minutes"] = {
            "mean": round(statistics.mean(completion_times), 2),
            "median": round(statistics.median(completion_times), 2),
            "min": round(min(completion_times), 2),
            "max": round(max(completion_times), 2)
        }
    
    return summary


def _export_responses_csv(responses: List[Response], survey: Survey, include_personal_data: bool):
    """Export responses as CSV."""
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    output = io.StringIO()
    
    # Get all unique question IDs
    all_questions = set()
    for response in responses:
        all_questions.update(response.answers.keys())
    
    all_questions = sorted(list(all_questions))
    
    # Create CSV writer
    writer = csv.writer(output)
    
    # Write header
    header = ["response_id", "submitted_at"]
    if include_personal_data:
        header.extend(["respondent_id", "ip_address"])
    header.extend(all_questions)
    writer.writerow(header)
    
    # Write data
    for response in responses:
        row = [response.id, response.submitted_at.isoformat()]
        
        if include_personal_data:
            row.extend([response.respondent_id, response.ip_address])
        
        for question_id in all_questions:
            answer = response.answers.get(question_id, "")
            if isinstance(answer, (list, dict)):
                answer = str(answer)
            row.append(answer)
        
        writer.writerow(row)
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=survey_{survey.id}_responses.csv"}
    )


def _export_responses_json(responses: List[Response], survey: Survey, include_personal_data: bool):
    """Export responses as JSON."""
    from fastapi.responses import JSONResponse
    
    exported_responses = []
    
    for response in responses:
        response_data = {
            "response_id": response.id,
            "submitted_at": response.submitted_at.isoformat(),
            "answers": response.answers
        }
        
        if include_personal_data:
            response_data.update({
                "respondent_id": response.respondent_id,
                "ip_address": response.ip_address,
                "user_agent": response.user_agent
            })
        
        exported_responses.append(response_data)
    
    return JSONResponse(
        content={
            "survey_id": survey.id,
            "survey_title": survey.title,
            "export_date": datetime.utcnow().isoformat(),
            "total_responses": len(responses),
            "responses": exported_responses
        },
        headers={"Content-Disposition": f"attachment; filename=survey_{survey.id}_responses.json"}
    )


def _export_responses_xlsx(responses: List[Response], survey: Survey, include_personal_data: bool):
    """Export responses as Excel file."""
    import pandas as pd
    import io
    from fastapi.responses import StreamingResponse
    
    # Prepare data for DataFrame
    data = []
    
    for response in responses:
        row = {
            "response_id": response.id,
            "submitted_at": response.submitted_at
        }
        
        if include_personal_data:
            row.update({
                "respondent_id": response.respondent_id,
                "ip_address": response.ip_address
            })
        
        # Add answers
        for question_id, answer in response.answers.items():
            if isinstance(answer, (list, dict)):
                row[question_id] = str(answer)
            else:
                row[question_id] = answer
        
        data.append(row)
    
    # Create DataFrame and Excel file
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Responses', index=False)
    
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=survey_{survey.id}_responses.xlsx"}
    )
