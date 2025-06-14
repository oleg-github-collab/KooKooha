"""Payment service for Stripe integration."""
from typing import Dict, Any, Optional
from datetime import datetime

import stripe
from sqlmodel import Session, select
import structlog

from ..models import Payment, PaymentStatus, Organization
from ..config import settings


logger = structlog.get_logger()


class PaymentService:
    """Service for handling payments via Stripe."""
    
    def __init__(self, session: Session):
        self.session = session
        stripe.api_key = settings.stripe_secret_key
    
    async def create_checkout_session(
        self,
        org_id: int,
        team_size: int,
        criteria_count: int,
        success_url: str,
        cancel_url: str,
        customer_email: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a Stripe checkout session."""
        # Calculate total price
        total_price_cents = settings.calculate_price(team_size, criteria_count)
        
        # Create payment record
        payment = Payment(
            org_id=org_id,
            amount_cents=total_price_cents,
            currency="EUR",
            team_size=team_size,
            criteria_count=criteria_count,
            status=PaymentStatus.PENDING,
            metadata=metadata or {}
        )
        
        self.session.add(payment)
        self.session.commit()
        self.session.refresh(payment)
        
        try:
            # Create Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': 'Human Lens Survey Assessment',
                                'description': f'Team assessment for {team_size} people with {criteria_count} criteria',
                                'images': [],  # Add product images if available
                            },
                            'unit_amount': total_price_cents,
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata={
                    'payment_id': str(payment.id),
                    'org_id': str(org_id),
                    'team_size': str(team_size),
                    'criteria_count': str(criteria_count),
                    **metadata
                },
                automatic_tax={'enabled': True},
                billing_address_collection='required',
                invoice_creation={'enabled': True},
                payment_intent_data={
                    'metadata': {
                        'payment_id': str(payment.id),
                        'org_id': str(org_id),
                    }
                }
            )
            
            # Update payment with session ID
            payment.stripe_session_id = checkout_session.id
            self.session.add(payment)
            self.session.commit()
            
            logger.info(
                "Checkout session created",
                payment_id=payment.id,
                session_id=checkout_session.id,
                amount_cents=total_price_cents
            )
            
            return {
                "session_id": checkout_session.id,
                "session_url": checkout_session.url,
                "payment_id": payment.id
            }
            
        except stripe.error.StripeError as e:
            # Update payment status to failed
            payment.status = PaymentStatus.FAILED
            payment.metadata = {**payment.metadata, "stripe_error": str(e)}
            self.session.add(payment)
            self.session.commit()
            
            logger.error(
                "Failed to create Stripe session",
                payment_id=payment.id,
                error=str(e)
            )
            
            raise Exception(f"Failed to create checkout session: {str(e)}")
    
    async def handle_webhook_event(self, event: Dict[str, Any]) -> None:
        """Handle Stripe webhook events."""
        event_type = event['type']
        data = event['data']['object']
        
        logger.info(
            "Processing webhook event",
            event_type=event_type,
            event_id=event['id']
        )
        
        if event_type == 'checkout.session.completed':
            await self._handle_checkout_completed(data)
        
        elif event_type == 'payment_intent.succeeded':
            await self._handle_payment_succeeded(data)
        
        elif event_type == 'payment_intent.payment_failed':
            await self._handle_payment_failed(data)
        
        elif event_type == 'charge.dispute.created':
            await self._handle_dispute_created(data)
        
        elif event_type == 'invoice.payment_succeeded':
            await self._handle_invoice_payment_succeeded(data)
        
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
    
    async def _handle_checkout_completed(self, session_data: Dict[str, Any]) -> None:
        """Handle checkout session completion."""
        session_id = session_data['id']
        
        # Get payment record
        payment = self.session.exec(
            select(Payment).where(Payment.stripe_session_id == session_id)
        ).first()
        
        if not payment:
            logger.error(f"Payment not found for session {session_id}")
            return
        
        # Update payment record
        payment.stripe_payment_intent_id = session_data.get('payment_intent')
        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = datetime.utcnow()
        
        # Add additional metadata from session
        payment.metadata = {
            **payment.metadata,
            "customer_email": session_data.get('customer_email'),
            "customer_details": session_data.get('customer_details', {}),
            "amount_total": session_data.get('amount_total'),
        }
        
        self.session.add(payment)
        self.session.commit()
        
        logger.info(
            "Payment completed",
            payment_id=payment.id,
            session_id=session_id,
            amount_cents=payment.amount_cents
        )
        
        # Trigger post-payment actions
        await self._trigger_post_payment_actions(payment)
    
    async def _handle_payment_succeeded(self, payment_intent_data: Dict[str, Any]) -> None:
        """Handle successful payment intent."""
        payment_intent_id = payment_intent_data['id']
        
        # Get payment record
        payment = self.session.exec(
            select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
        ).first()
        
        if not payment:
            logger.warning(f"Payment not found for payment intent {payment_intent_id}")
            return
        
        # Ensure payment is marked as completed
        if payment.status != PaymentStatus.COMPLETED:
            payment.status = PaymentStatus.COMPLETED
            payment.paid_at = datetime.utcnow()
            self.session.add(payment)
            self.session.commit()
        
        logger.info(
            "Payment intent succeeded",
            payment_id=payment.id,
            payment_intent_id=payment_intent_id
        )
    
    async def _handle_payment_failed(self, payment_intent_data: Dict[str, Any]) -> None:
        """Handle failed payment intent."""
        payment_intent_id = payment_intent_data['id']
        
        # Get payment record
        payment = self.session.exec(
            select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
        ).first()
        
        if not payment:
            logger.warning(f"Payment not found for failed payment intent {payment_intent_id}")
            return
        
        # Update payment status
        payment.status = PaymentStatus.FAILED
        payment.metadata = {
            **payment.metadata,
            "failure_reason": payment_intent_data.get('last_payment_error', {}).get('message'),
            "failure_code": payment_intent_data.get('last_payment_error', {}).get('code'),
        }
        
        self.session.add(payment)
        self.session.commit()
        
        logger.error(
            "Payment failed",
            payment_id=payment.id,
            payment_intent_id=payment_intent_id,
            reason=payment.metadata.get('failure_reason')
        )
    
    async def _handle_dispute_created(self, dispute_data: Dict[str, Any]) -> None:
        """Handle payment dispute creation."""
        charge_id = dispute_data.get('charge')
        
        # Log dispute for investigation
        logger.warning(
            "Payment dispute created",
            dispute_id=dispute_data['id'],
            charge_id=charge_id,
            amount=dispute_data.get('amount'),
            reason=dispute_data.get('reason')
        )
        
        # Dispute handling logic should go here:
        # - Find related payment
        # - Update payment status
        # - Send notification to admin
        # - Create dispute record
    
    async def _handle_invoice_payment_succeeded(self, invoice_data: Dict[str, Any]) -> None:
        """Handle successful invoice payment."""
        invoice_id = invoice_data['id']
        
        logger.info(
            "Invoice payment succeeded",
            invoice_id=invoice_id,
            amount_paid=invoice_data.get('amount_paid')
        )
        
        # Placeholder for invoice-specific logic if needed
    
    async def _trigger_post_payment_actions(self, payment: Payment) -> None:
        """Trigger actions after successful payment."""
        try:
            # Get organization
            organization = self.session.get(Organization, payment.org_id)
            if not organization:
                logger.error(f"Organization not found for payment {payment.id}")
                return
            
            # Post-payment actions could include:
            # 1. Send payment confirmation email
            # 2. Update organization credit/balance
            # 3. Enable survey creation
            # 4. Send receipt
            # 5. Update analytics
            
            logger.info(
                "Post-payment actions triggered",
                payment_id=payment.id,
                org_id=payment.org_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to trigger post-payment actions",
                payment_id=payment.id,
                error=str(e)
            )
    
    async def process_refund(
        self,
        payment_id: int,
        reason: Optional[str] = None,
        amount_cents: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process a refund for a payment."""
        payment = self.session.get(Payment, payment_id)
        if not payment:
            raise ValueError("Payment not found")
        
        if payment.status != PaymentStatus.COMPLETED:
            raise ValueError("Only completed payments can be refunded")
        
        if not payment.stripe_payment_intent_id:
            raise ValueError("No Stripe payment intent found")
        
        try:
            # Create refund in Stripe
            refund_amount = amount_cents or payment.amount_cents
            
            refund = stripe.Refund.create(
                payment_intent=payment.stripe_payment_intent_id,
                amount=refund_amount,
                reason=reason or 'requested_by_customer',
                metadata={
                    'payment_id': str(payment_id),
                    'org_id': str(payment.org_id),
                    'original_amount': str(payment.amount_cents)
                }
            )
            
            # Update payment record
            if refund_amount >= payment.amount_cents:
                payment.status = PaymentStatus.REFUNDED
            
            payment.refunded_at = datetime.utcnow()
            payment.metadata = {
                **payment.metadata,
                "refund_id": refund.id,
                "refund_amount": refund_amount,
                "refund_reason": reason
            }
            
            self.session.add(payment)
            self.session.commit()
            
            logger.info(
                "Refund processed",
                payment_id=payment_id,
                refund_id=refund.id,
                refund_amount=refund_amount
            )
            
            return {
                "refund_id": refund.id,
                "amount": refund_amount,
                "status": refund.status,
                "reason": reason
            }
            
        except stripe.error.StripeError as e:
            logger.error(
                "Failed to process refund",
                payment_id=payment_id,
                error=str(e)
            )
            raise Exception(f"Failed to process refund: {str(e)}")
    
    async def get_payment_methods(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get saved payment methods for a customer."""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            
            return [
                {
                    "id": pm.id,
                    "type": pm.type,
                    "card": {
                        "brand": pm.card.brand,
                        "last4": pm.card.last4,
                        "exp_month": pm.card.exp_month,
                        "exp_year": pm.card.exp_year
                    } if pm.card else None,
                    "billing_details": pm.billing_details
                }
                for pm in payment_methods.data
            ]
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve payment methods: {str(e)}")
            return []
    
    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        organization_name: Optional[str] = None
    ) -> str:
        """Create a Stripe customer."""
        try:
            customer_data = {
                "email": email,
                "description": f"Customer for {organization_name}" if organization_name else None
            }
            
            if name:
                customer_data["name"] = name
            
            customer = stripe.Customer.create(**customer_data)
            
            logger.info(
                "Stripe customer created",
                customer_id=customer.id,
                email=email
            )
            
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {str(e)}")
            raise Exception(f"Failed to create customer: {str(e)}")
    
    async def get_payment_analytics(
        self,
        org_id: int,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get payment analytics for organization."""
        # Get payments from database
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        payments = self.session.exec(
            select(Payment).where(
                Payment.org_id == org_id,
                Payment.created_at >= cutoff_date
            )
        ).all()
        
        # Calculate metrics
        total_payments = len(payments)
        successful_payments = len([p for p in payments if p.status == PaymentStatus.COMPLETED])
        failed_payments = len([p for p in payments if p.status == PaymentStatus.FAILED])
        refunded_payments = len([p for p in payments if p.status == PaymentStatus.REFUNDED])
        
        total_revenue = sum(
            p.amount_cents for p in payments 
            if p.status == PaymentStatus.COMPLETED
        )
        
        # Calculate conversion rate
        conversion_rate = (successful_payments / total_payments * 100) if total_payments > 0 else 0
        
        return {
            "period_days": period_days,
            "total_payments": total_payments,
            "successful_payments": successful_payments,
            "failed_payments": failed_payments,
            "refunded_payments": refunded_payments,
            "conversion_rate": round(conversion_rate, 2),
            "total_revenue_cents": total_revenue,
            "total_revenue_eur": total_revenue / 100,
            "average_payment_eur": (total_revenue / successful_payments / 100) if successful_payments > 0 else 0
        }
    
    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: str
    ) -> bool:
        """Validate Stripe webhook signature."""
        try:
            stripe.Webhook.construct_event(payload, signature, webhook_secret)
            return True
        except (ValueError, stripe.error.SignatureVerificationError):
            return False
