"""Payment processing routes using Stripe."""
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlmodel import Session, select
from pydantic import BaseModel, validator
import stripe
import structlog

from ..database import get_session
from ..models import (
    Payment, PaymentCreate, PaymentRead, PaymentStatus,
    User, Organization
)
from ..auth import get_current_user, require_client_admin, verify_organization_access
from ..services.payment_service import PaymentService
from ..config import settings


logger = structlog.get_logger()
router = APIRouter()

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key


class PaymentCalculationRequest(BaseModel):
    """Payment calculation request model."""
    team_size: int
    criteria_count: int
    
    @validator('team_size')
    def validate_team_size(cls, v):
        if v < 1 or v > settings.max_team_size:
            raise ValueError(f'Team size must be between 1 and {settings.max_team_size}')
        return v
    
    @validator('criteria_count')
    def validate_criteria_count(cls, v):
        if v < 1 or v > settings.max_criteria_count:
            raise ValueError(f'Criteria count must be between 1 and {settings.max_criteria_count}')
        return v


class PaymentCalculationResponse(BaseModel):
    """Payment calculation response model."""
    base_price_cents: int
    additional_people_cost: int
    additional_criteria_cost: int
    total_price_cents: int
    total_price_eur: float
    breakdown: Dict[str, Any]


class CheckoutSessionRequest(BaseModel):
    """Checkout session creation request."""
    team_size: int
    criteria_count: int
    success_url: str
    cancel_url: str
    metadata: Optional[Dict[str, str]] = None


class CheckoutSessionResponse(BaseModel):
    """Checkout session response model."""
    session_id: str
    session_url: str
    payment_id: int


@router.post("/calculate", response_model=PaymentCalculationResponse)
async def calculate_payment(
    calculation: PaymentCalculationRequest,
    current_user: User = Depends(get_current_user)
):
    """Calculate payment amount based on team size and criteria count."""
    # Calculate pricing
    total_price_cents = settings.calculate_price(
        team_size=calculation.team_size,
        criteria_count=calculation.criteria_count
    )
    
    # Calculate component costs
    additional_people = max(0, calculation.team_size - settings.base_team_size)
    additional_criteria = max(0, calculation.criteria_count - settings.base_criteria_count)
    
    additional_people_cost = additional_people * settings.price_per_additional_person_cents
    additional_criteria_cost = additional_criteria * settings.price_per_additional_criteria_cents
    
    # Create breakdown
    breakdown = {
        "base_package": {
            "description": f"Base package ({settings.base_team_size} people, {settings.base_criteria_count} criteria)",
            "price_cents": settings.base_price_cents,
            "price_eur": settings.base_price_cents / 100
        },
        "additional_people": {
            "count": additional_people,
            "price_per_person_cents": settings.price_per_additional_person_cents,
            "total_price_cents": additional_people_cost,
            "price_eur": additional_people_cost / 100
        },
        "additional_criteria": {
            "count": additional_criteria,
            "price_per_criteria_cents": settings.price_per_additional_criteria_cents,
            "total_price_cents": additional_criteria_cost,
            "price_eur": additional_criteria_cost / 100
        }
    }
    
    logger.info(
        "Payment calculated",
        user_id=current_user.id,
        team_size=calculation.team_size,
        criteria_count=calculation.criteria_count,
        total_price_cents=total_price_cents
    )
    
    return PaymentCalculationResponse(
        base_price_cents=settings.base_price_cents,
        additional_people_cost=additional_people_cost,
        additional_criteria_cost=additional_criteria_cost,
        total_price_cents=total_price_cents,
        total_price_eur=total_price_cents / 100,
        breakdown=breakdown
    )


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    checkout_request: CheckoutSessionRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_client_admin)
):
    """Create Stripe checkout session."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be associated with an organization"
        )
    
    # Get organization
    organization = session.get(Organization, current_user.org_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    payment_service = PaymentService(session)
    
    try:
        # Create payment record and Stripe session
        result = await payment_service.create_checkout_session(
            org_id=current_user.org_id,
            team_size=checkout_request.team_size,
            criteria_count=checkout_request.criteria_count,
            success_url=checkout_request.success_url,
            cancel_url=checkout_request.cancel_url,
            customer_email=current_user.email,
            metadata=checkout_request.metadata or {}
        )
        
        logger.info(
            "Checkout session created",
            user_id=current_user.id,
            org_id=current_user.org_id,
            session_id=result["session_id"],
            payment_id=result["payment_id"]
        )
        
        return CheckoutSessionResponse(
            session_id=result["session_id"],
            session_url=result["session_url"],
            payment_id=result["payment_id"]
        )
        
    except Exception as e:
        logger.error(
            "Failed to create checkout session",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    session: Session = Depends(get_session)
):
    """Handle Stripe webhook events."""
    payload = await request.body()
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError:
        logger.error("Invalid payload in Stripe webhook")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature in Stripe webhook")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    payment_service = PaymentService(session)
    
    try:
        # Handle the event
        await payment_service.handle_webhook_event(event)
        
        logger.info(
            "Webhook processed successfully",
            event_type=event["type"],
            event_id=event["id"]
        )
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(
            "Failed to process webhook",
            event_type=event.get("type"),
            event_id=event.get("id"),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )


@router.get("/history/{org_id}", response_model=List[PaymentRead])
async def get_payment_history(
    org_id: int,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get payment history for organization."""
    await verify_organization_access(org_id, current_user)
    
    # Get payments for organization
    query = select(Payment).where(
        Payment.org_id == org_id
    ).order_by(
        Payment.created_at.desc()
    ).offset(offset).limit(limit)
    
    payments = session.exec(query).all()
    
    return [PaymentRead.model_validate(payment) for payment in payments]


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get payment details."""
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    await verify_organization_access(payment.org_id, current_user)
    
    return PaymentRead.model_validate(payment)


@router.get("/session/{session_id}/status")
async def get_checkout_session_status(
    session_id: str,
    db_session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get checkout session status."""
    try:
        # Get session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Get payment record
        payment = db_session.exec(
            select(Payment).where(Payment.stripe_session_id == session_id)
        ).first()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        await verify_organization_access(payment.org_id, current_user)
        
        return {
            "session_id": session_id,
            "payment_status": checkout_session.payment_status,
            "payment_id": payment.id,
            "amount_total": checkout_session.amount_total,
            "currency": checkout_session.currency,
            "customer_email": checkout_session.customer_email,
            "payment_intent": checkout_session.payment_intent
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error retrieving session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID"
        )


@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    reason: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_client_admin)
):
    """Request a refund for a payment."""
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    await verify_organization_access(payment.org_id, current_user)
    
    if payment.status != PaymentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed payments can be refunded"
        )
    
    payment_service = PaymentService(session)
    
    try:
        refund_result = await payment_service.process_refund(
            payment_id=payment_id,
            reason=reason
        )
        
        logger.info(
            "Refund processed",
            payment_id=payment_id,
            refund_id=refund_result.get("refund_id"),
            requested_by=current_user.id
        )
        
        return {
            "message": "Refund processed successfully",
            "refund_id": refund_result.get("refund_id"),
            "amount": refund_result.get("amount"),
            "status": refund_result.get("status")
        }
        
    except Exception as e:
        logger.error(f"Failed to process refund: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process refund"
        )


@router.get("/config/public")
async def get_public_payment_config():
    """Get public payment configuration."""
    return {
        "stripe_publishable_key": settings.stripe_publishable_key,
        "base_price_cents": settings.base_price_cents,
        "base_team_size": settings.base_team_size,
        "base_criteria_count": settings.base_criteria_count,
        "price_per_additional_person_cents": settings.price_per_additional_person_cents,
        "price_per_additional_criteria_cents": settings.price_per_additional_criteria_cents,
        "max_team_size": settings.max_team_size,
        "max_criteria_count": settings.max_criteria_count,
        "currency": "EUR"
    }


@router.get("/invoices/{org_id}")
async def get_invoices(
    org_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get invoices for organization from Stripe."""
    await verify_organization_access(org_id, current_user)
    
    # Get organization
    organization = session.get(Organization, org_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    try:
        # Get customer ID from Stripe (if exists)
        # This would require storing customer ID in organization or payment records
        # For now, return empty list
        
        return {
            "organization_id": org_id,
            "invoices": [],
            "message": "Invoice retrieval not yet implemented"
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve invoices: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invoices"
        )


@router.get("/analytics/{org_id}")
async def get_payment_analytics(
    org_id: int,
    period_days: int = 365,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get payment analytics for organization."""
    await verify_organization_access(org_id, current_user)
    
    # Get payments for the period
    cutoff_date = datetime.utcnow() - timedelta(days=period_days)
    
    query = select(Payment).where(
        Payment.org_id == org_id,
        Payment.created_at >= cutoff_date
    )
    
    payments = session.exec(query).all()
    
    # Calculate analytics
    total_payments = len(payments)
    completed_payments = len([p for p in payments if p.status == PaymentStatus.COMPLETED])
    total_amount = sum(p.amount_cents for p in payments if p.status == PaymentStatus.COMPLETED)
    
    # Group by month
    monthly_totals = {}
    for payment in payments:
        if payment.status == PaymentStatus.COMPLETED:
            month_key = payment.created_at.strftime("%Y-%m")
            monthly_totals[month_key] = monthly_totals.get(month_key, 0) + payment.amount_cents
    
    return {
        "organization_id": org_id,
        "period_days": period_days,
        "total_payments": total_payments,
        "completed_payments": completed_payments,
        "success_rate": (completed_payments / total_payments * 100) if total_payments > 0 else 0,
        "total_amount_cents": total_amount,
        "total_amount_eur": total_amount / 100,
        "monthly_totals": {k: v / 100 for k, v in monthly_totals.items()},
        "average_payment_eur": (total_amount / completed_payments / 100) if completed_payments > 0 else 0
    }
