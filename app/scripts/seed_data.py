#!/usr/bin/env python3
"""Seed database with sample data for development and testing."""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List

from faker import Faker
from sqlmodel import Session

from app.auth import get_password_hash
from app.database import create_db_and_tables, get_session
from app.models import (
    Organization,
    User,
    UserRole,
    Survey,
    SurveyType,
    SurveyStatus,
    Question,
    QuestionType,
    SurveyInvitation,
    Response,
    Payment,
    PaymentStatus,
)


fake = Faker()


class DataSeeder:
    """Class for seeding database with sample data."""
    
    def __init__(self):
        self.session = next(get_session())
        self.organizations: List[Organization] = []
        self.users: List[User] = []
        self.surveys: List[Survey] = []
        self.questions: List[Question] = []
    
    async def seed_all(self):
        """Seed all sample data."""
        print("🌱 Starting database seeding...")
        
        # Create database tables
        create_db_and_tables()
        
        # Seed data in order
        await self.seed_questions()
        await self.seed_organizations()
        await self.seed_users()
        await self.seed_surveys()
        await self.seed_survey_invitations()
        await self.seed_responses()
        await self.seed_payments()
        
        self.session.commit()
        print("✅ Database seeding completed!")
    
    async def seed_questions(self):
        """Seed question templates."""
        print("📝 Seeding question templates...")
        
        # Sociometry questions
        sociometry_questions = [
            {
                "text": "Who do you most often collaborate with on work projects?",
                "question_type": QuestionType.SOCIOMETRIC,
                "category": "collaboration",
                "order_index": 1,
                "options": {"max_selections": 5, "min_selections": 1}
            },
            {
                "text": "Who would you turn to for advice on difficult work problems?",
                "question_type": QuestionType.SOCIOMETRIC,
                "category": "advice",
                "order_index": 2,
                "options": {"max_selections": 3, "min_selections": 1}
            },
            {
                "text": "Who do you think has the most influence in team decisions?",
                "question_type": QuestionType.SOCIOMETRIC,
                "category": "influence",
                "order_index": 3,
                "options": {"max_selections": 3, "min_selections": 1}
            },
            {
                "text": "Who do you enjoy working with the most?",
                "question_type": QuestionType.SOCIOMETRIC,
                "category": "enjoyment",
                "order_index": 4,
                "options": {"max_selections": 5, "min_selections": 1}
            },
            {
                "text": "Who do you think brings the most innovative ideas to the team?",
                "question_type": QuestionType.SOCIOMETRIC,
                "category": "innovation",
                "order_index": 5,
                "options": {"max_selections": 3, "min_selections": 1}
            }
        ]
        
        for q_data in sociometry_questions:
            question = Question(
                **q_data,
                survey_type=SurveyType.SOCIOMETRY,
                is_active=True
            )
            self.session.add(question)
            self.questions.append(question)
        
        # eNPS questions
        enps_questions = [
            {
                "text": "How likely are you to recommend this company as a place to work to a friend or colleague?",
                "question_type": QuestionType.RATING,
                "category": "nps",
                "order_index": 1,
                "options": {"min_value": 0, "max_value": 10, "scale_type": "nps"}
            },
            {
                "text": "What is the main reason for your score?",
                "question_type": QuestionType.TEXT,
                "category": "feedback",
                "order_index": 2,
                "options": {"max_length": 500}
            },
            {
                "text": "How satisfied are you with your current role?",
                "question_type": QuestionType.RATING,
                "category": "satisfaction",
                "order_index": 3,
                "options": {"min_value": 1, "max_value": 5, "scale_type": "satisfaction"}
            }
        ]
        
        for q_data in enps_questions:
            question = Question(
                **q_data,
                survey_type=SurveyType.ENPS,
                is_active=True
            )
            self.session.add(question)
            self.questions.append(question)
        
        # 360 Review questions
        review_360_questions = [
            {
                "text": "How effectively does this person communicate with team members?",
                "question_type": QuestionType.RATING,
                "category": "communication",
                "order_index": 1,
                "options": {"min_value": 1, "max_value": 5, "scale_type": "effectiveness"}
            },
            {
                "text": "How well does this person demonstrate leadership qualities?",
                "question_type": QuestionType.RATING,
                "category": "leadership",
                "order_index": 2,
                "options": {"min_value": 1, "max_value": 5, "scale_type": "effectiveness"}
            },
            {
                "text": "How reliable is this person in meeting deadlines and commitments?",
                "question_type": QuestionType.RATING,
                "category": "reliability",
                "order_index": 3,
                "options": {"min_value": 1, "max_value": 5, "scale_type": "effectiveness"}
            },
            {
                "text": "What are this person's greatest strengths?",
                "question_type": QuestionType.TEXT,
                "category": "strengths",
                "order_index": 4,
                "options": {"max_length": 300}
            },
            {
                "text": "What areas could this person improve in?",
                "question_type": QuestionType.TEXT,
                "category": "improvement",
                "order_index": 5,
                "options": {"max_length": 300}
            }
        ]
        
        for q_data in review_360_questions:
            question = Question(
                **q_data,
                survey_type=SurveyType.REVIEW_360,
                is_active=True
            )
            self.session.add(question)
            self.questions.append(question)
        
        print(f"   Created {len(self.questions)} question templates")
    
    async def seed_organizations(self):
        """Seed sample organizations."""
        print("🏢 Seeding organizations...")
        
        org_data = [
            {
                "name": "TechFlow Solutions",
                "description": "A fast-growing software development company",
                "website": "https://techflow.com",
                "industry": "Technology"
            },
            {
                "name": "GreenEnergy Corp",
                "description": "Renewable energy solutions provider",
                "website": "https://greenenergy.com",
                "industry": "Energy"
            },
            {
                "name": "HealthFirst Medical",
                "description": "Healthcare technology and services",
                "website": "https://healthfirst.com",
                "industry": "Healthcare"
            }
        ]
        
        for data in org_data:
            org = Organization(**data)
            self.session.add(org)
            self.organizations.append(org)
        
        print(f"   Created {len(self.organizations)} organizations")
    
    async def seed_users(self):
        """Seed sample users."""
        print("👥 Seeding users...")
        
        departments = ["Engineering", "Marketing", "Sales", "HR", "Finance", "Operations"]
        positions = ["Manager", "Senior", "Lead", "Specialist", "Coordinator", "Analyst"]
        
        # Create super admin
        super_admin = User(
            email="admin@kookooha.com",
            first_name="Super",
            last_name="Admin",
            role=UserRole.SUPERADMIN,
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_verified=True
        )
        self.session.add(super_admin)
        self.users.append(super_admin)
        
        # Create client admins and respondents for each organization
        for org in self.organizations:
            # Create client admin
            admin = User(
                email=f"admin@{org.name.lower().replace(' ', '')}.com",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                role=UserRole.CLIENTADMIN,
                org_id=org.id,
                hashed_password=get_password_hash("password123"),
                is_active=True,
                is_verified=True
            )
            self.session.add(admin)
            self.users.append(admin)
            
            # Create 15-25 respondents per organization
            num_respondents = random.randint(15, 25)
            for i in range(num_respondents):
                user = User(
                    email=fake.email(),
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    role=UserRole.RESPONDENT,
                    org_id=org.id,
                    department=random.choice(departments),
                    position=f"{random.choice(positions)} {fake.job()}",
                    employee_id=f"EMP{random.randint(1000, 9999)}",
                    is_active=True,
                    is_verified=random.choice([True, False])
                )
                self.session.add(user)
                self.users.append(user)
        
        print(f"   Created {len(self.users)} users")
    
    async def seed_surveys(self):
        """Seed sample surveys."""
        print("📊 Seeding surveys...")
        
        survey_titles = {
            SurveyType.SOCIOMETRY: [
                "Q4 Team Dynamics Assessment",
                "Project Alpha Team Analysis",
                "Cross-Department Collaboration Study"
            ],
            SurveyType.ENPS: [
                "Employee Satisfaction Survey 2024",
                "Quarterly Engagement Check",
                "Annual Employee Net Promoter Score"
            ],
            SurveyType.REVIEW_360: [
                "Leadership Development Review",
                "Mid-Year Performance Assessment",
                "Senior Management 360 Review"
            ],
            SurveyType.TEAM_DYNAMICS: [
                "Team Effectiveness Analysis",
                "Communication Patterns Study",
                "Collaboration Optimization Survey"
            ]
        }
        
        statuses = [SurveyStatus.ACTIVE, SurveyStatus.CLOSED, SurveyStatus.DRAFT]
        
        for org in self.organizations:
            # Create 3-5 surveys per organization
            num_surveys = random.randint(3, 5)
            
            for _ in range(num_surveys):
                survey_type = random.choice(list(SurveyType))
                status = random.choice(statuses)
                
                # Set dates based on status
                created_at = fake.date_time_between(start_date='-6M', end_date='now')
                scheduled_at = None
                activated_at = None
                closed_at = None
                
                if status in [SurveyStatus.ACTIVE, SurveyStatus.CLOSED]:
                    scheduled_at = created_at + timedelta(days=random.randint(1, 7))
                    activated_at = scheduled_at + timedelta(hours=random.randint(1, 24))
                    
                    if status == SurveyStatus.CLOSED:
                        closed_at = activated_at + timedelta(days=random.randint(7, 21))
                
                survey = Survey(
                    title=random.choice(survey_titles[survey_type]),
                    description=fake.paragraph(nb_sentences=3),
                    survey_type=survey_type,
                    org_id=org.id,
                    status=status,
                    criteria=self._generate_survey_criteria(survey_type),
                    scheduled_at=scheduled_at,
                    activated_at=activated_at,
                    closed_at=closed_at,
                    anonymize_responses=random.choice([True, False]),
                    reminder_enabled=True,
                    reminder_days=random.randint(2, 5),
                    auto_close_days=random.randint(14, 30),
                    created_at=created_at
                )
                self.session.add(survey)
                self.surveys.append(survey)
        
        print(f"   Created {len(self.surveys)} surveys")
    
    def _generate_survey_criteria(self, survey_type: SurveyType) -> dict:
        """Generate criteria based on survey type."""
        base_criteria = {
            "required_questions": [],
            "question_types": {},
            "settings": {}
        }
        
        if survey_type == SurveyType.SOCIOMETRY:
            base_criteria.update({
                "max_selections_per_question": 5,
                "min_selections_per_question": 1,
                "allow_self_selection": False
            })
        elif survey_type == SurveyType.ENPS:
            base_criteria.update({
                "nps_question_required": True,
                "follow_up_questions": True
            })
        elif survey_type == SurveyType.REVIEW_360:
            base_criteria.update({
                "peer_review_enabled": True,
                "manager_review_enabled": True,
                "self_review_enabled": True
            })
        
        return base_criteria
    
    async def seed_survey_invitations(self):
        """Seed survey invitations."""
        print("📧 Seeding survey invitations...")
        
        invitations_created = 0
        
        for survey in self.surveys:
            if survey.status in [SurveyStatus.ACTIVE, SurveyStatus.CLOSED]:
                # Get respondents from the same organization
                org_users = [u for u in self.users if u.org_id == survey.org_id and u.role == UserRole.RESPONDENT]
                
                # Invite 60-90% of users
                num_invites = int(len(org_users) * random.uniform(0.6, 0.9))
                invited_users = random.sample(org_users, num_invites)
                
                for user in invited_users:
                    # Generate token (simplified for seeding)
                    token = fake.uuid4()
                    
                    expires_at = survey.activated_at + timedelta(days=30) if survey.activated_at else datetime.utcnow() + timedelta(days=30)
                    sent_at = survey.activated_at if survey.activated_at else None
                    
                    # Some invitations are opened/completed
                    opened_at = None
                    completed_at = None
                    
                    if sent_at and random.random() < 0.7:  # 70% open rate
                        opened_at = sent_at + timedelta(hours=random.randint(1, 48))
                        
                        if random.random() < 0.6:  # 60% completion rate among opened
                            completed_at = opened_at + timedelta(minutes=random.randint(5, 30))
                    
                    invitation = SurveyInvitation(
                        survey_id=survey.id,
                        respondent_id=user.id,
                        email=user.email,
                        token=token,
                        expires_at=expires_at,
                        sent_at=sent_at,
                        opened_at=opened_at,
                        completed_at=completed_at,
                        reminder_count=random.randint(0, 2) if sent_at else 0
                    )
                    self.session.add(invitation)
                    invitations_created += 1
        
        print(f"   Created {invitations_created} survey invitations")
    
    async def seed_responses(self):
        """Seed survey responses."""
        print("💬 Seeding survey responses...")
        
        responses_created = 0
        
        # Get all completed invitations
        completed_invitations = self.session.query(SurveyInvitation).filter(
            SurveyInvitation.completed_at.isnot(None)
        ).all()
        
        for invitation in completed_invitations:
            survey = next((s for s in self.surveys if s.id == invitation.survey_id), None)
            if not survey:
                continue
            
            # Generate response based on survey type
            answers = self._generate_response_answers(survey.survey_type, survey.org_id)
            
            response = Response(
                survey_id=survey.id,
                respondent_id=invitation.respondent_id,
                invitation_id=invitation.id,
                answers=answers,
                submitted_at=invitation.completed_at,
                ip_address=fake.ipv4(),
                user_agent=fake.user_agent()
            )
            self.session.add(response)
            responses_created += 1
        
        print(f"   Created {responses_created} survey responses")
    
    def _generate_response_answers(self, survey_type: SurveyType, org_id: int) -> dict:
        """Generate realistic response answers based on survey type."""
        answers = {}
        
        # Get users from the same organization for sociometric questions
        org_users = [u for u in self.users if u.org_id == org_id and u.role == UserRole.RESPONDENT]
        user_ids = [u.id for u in org_users]
        
        if survey_type == SurveyType.SOCIOMETRY:
            # Collaboration question
            answers["q1_collaboration"] = {
                "selections": random.sample(user_ids, min(random.randint(1, 3), len(user_ids)))
            }
            # Advice question
            answers["q2_advice"] = {
                "selections": random.sample(user_ids, min(random.randint(1, 2), len(user_ids)))
            }
            # Influence question
            answers["q3_influence"] = {
                "selections": random.sample(user_ids, min(random.randint(1, 2), len(user_ids)))
            }
            
        elif survey_type == SurveyType.ENPS:
            # NPS score (0-10)
            nps_score = random.choices(
                range(11), 
                weights=[2, 2, 3, 4, 5, 6, 8, 12, 15, 20, 25]  # Weighted towards higher scores
            )[0]
            answers["nps_score"] = nps_score
            
            # Reason for score
            if nps_score >= 9:
                reasons = ["Great team culture", "Excellent growth opportunities", "Amazing work-life balance"]
            elif nps_score >= 7:
                reasons = ["Good company overall", "Decent benefits", "Interesting work"]
            else:
                reasons = ["Limited growth opportunities", "High stress environment", "Poor management"]
            
            answers["nps_reason"] = random.choice(reasons)
            
            # Satisfaction rating (1-5)
            answers["satisfaction"] = random.randint(2, 5)
            
        elif survey_type == SurveyType.REVIEW_360:
            # Communication (1-5)
            answers["communication"] = random.randint(2, 5)
            # Leadership (1-5)
            answers["leadership"] = random.randint(2, 5)
            # Reliability (1-5)
            answers["reliability"] = random.randint(3, 5)
            # Strengths (text)
            strengths = [
                "Strong analytical skills", "Great team player", "Excellent communication",
                "Creative problem solver", "Natural leader", "Detail-oriented"
            ]
            answers["strengths"] = random.choice(strengths)
            # Areas for improvement
            improvements = [
                "Time management", "Public speaking", "Technical skills",
                "Delegation", "Strategic thinking", "Cross-team collaboration"
            ]
            answers["improvement"] = random.choice(improvements)
        
        return answers
    
    async def seed_payments(self):
        """Seed sample payments."""
        print("💳 Seeding payments...")
        
        payments_created = 0
        
        for org in self.organizations:
            # Create 1-3 payments per organization
            num_payments = random.randint(1, 3)
            
            for _ in range(num_payments):
                team_size = len([u for u in self.users if u.org_id == org.id and u.role == UserRole.RESPONDENT])
                criteria_count = random.randint(2, 8)
                
                # Calculate amount based on pricing model
                base_price = 75000  # €750
                additional_people = max(0, team_size - 4)
                additional_criteria = max(0, criteria_count - 2)
                
                amount_cents = (
                    base_price + 
                    (additional_people * 7500) + 
                    (additional_criteria * 15000)
                )
                
                status = random.choices(
                    [PaymentStatus.COMPLETED, PaymentStatus.PENDING, PaymentStatus.FAILED],
                    weights=[80, 15, 5]
                )[0]
                
                created_at = fake.date_time_between(start_date='-3M', end_date='now')
                paid_at = created_at + timedelta(minutes=random.randint(5, 60)) if status == PaymentStatus.COMPLETED else None
                
                payment = Payment(
                    org_id=org.id,
                    amount_cents=amount_cents,
                    currency="EUR",
                    team_size=team_size,
                    criteria_count=criteria_count,
                    status=status,
                    stripe_session_id=f"cs_{fake.uuid4()}",
                    stripe_payment_intent_id=f"pi_{fake.uuid4()}" if status == PaymentStatus.COMPLETED else None,
                    paid_at=paid_at,
                    created_at=created_at,
                    metadata={
                        "customer_email": f"admin@{org.name.lower().replace(' ', '')}.com",
                        "customer_name": org.name
                    }
                )
                self.session.add(payment)
                payments_created += 1
        
        print(f"   Created {payments_created} payments")


async def main():
    """Main seeding function."""
    seeder = DataSeeder()
    await seeder.seed_all()
    print("\n🎉 Database seeding completed successfully!")
    print("\n📊 Summary:")
    print(f"   Organizations: {len(seeder.organizations)}")
    print(f"   Users: {len(seeder.users)}")
    print(f"   Questions: {len(seeder.questions)}")
    print(f"   Surveys: {len(seeder.surveys)}")
    print("\n🔑 Login credentials:")
    print("   Super Admin: admin@kookooha.com / admin123")
    print("   Client Admins: admin@[orgname].com / password123")


if __name__ == "__main__":
    asyncio.run(main())
