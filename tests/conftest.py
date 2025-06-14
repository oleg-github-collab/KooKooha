"""Test configuration and fixtures."""
import os
import tempfile
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models import (
    User, UserRole, Organization, Survey, SurveyType, SurveyStatus,
    Question, QuestionType, Payment, PaymentStatus
)
from app.auth import get_password_hash, create_access_token


@pytest.fixture(scope="session")
def test_db():
    """Create a test database."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    # Create engine with test database
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create tables
    SQLModel.metadata.create_all(engine)
    
    yield engine
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def session(test_db) -> Generator[Session, None, None]:
    """Create a test database session."""
    with Session(test_db) as session:
        yield session


@pytest.fixture
def client(session: Session) -> TestClient:
    """Create a test client with database session override."""
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_organization(session: Session) -> Organization:
    """Create a test organization."""
    org = Organization(
        name="Test Organization",
        description="A test organization for unit testing",
        website="https://test.com",
        industry="Technology"
    )
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def test_superadmin(session: Session) -> User:
    """Create a test superadmin user."""
    user = User(
        email="superadmin@test.com",
        first_name="Super",
        last_name="Admin",
        role=UserRole.SUPERADMIN,
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_verified=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def test_client_admin(session: Session, test_organization: Organization) -> User:
    """Create a test client admin user."""
    user = User(
        email="admin@test.com",
        first_name="Test",
        last_name="Admin",
        role=UserRole.CLIENTADMIN,
        org_id=test_organization.id,
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_verified=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def test_respondent(session: Session, test_organization: Organization) -> User:
    """Create a test respondent user."""
    user = User(
        email="respondent@test.com",
        first_name="Test",
        last_name="Respondent",
        role=UserRole.RESPONDENT,
        org_id=test_organization.id,
        department="Engineering",
        position="Software Developer",
        employee_id="EMP001",
        is_active=True,
        is_verified=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def test_multiple_respondents(session: Session, test_organization: Organization) -> list[User]:
    """Create multiple test respondent users."""
    users = []
    departments = ["Engineering", "Marketing", "Sales", "HR"]
    
    for i in range(10):
        user = User(
            email=f"respondent{i}@test.com",
            first_name=f"Test{i}",
            last_name="Respondent",
            role=UserRole.RESPONDENT,
            org_id=test_organization.id,
            department=departments[i % len(departments)],
            position=f"Position {i}",
            employee_id=f"EMP00{i}",
            is_active=True,
            is_verified=True
        )
        session.add(user)
        users.append(user)
    
    session.commit()
    for user in users:
        session.refresh(user)
    
    return users


@pytest.fixture
def test_survey(session: Session, test_organization: Organization) -> Survey:
    """Create a test survey."""
    survey = Survey(
        title="Test Survey",
        description="A test survey for unit testing",
        survey_type=SurveyType.SOCIOMETRY,
        org_id=test_organization.id,
        status=SurveyStatus.DRAFT,
        criteria={"max_selections": 3, "min_selections": 1},
        anonymize_responses=True,
        reminder_enabled=True,
        reminder_days=3,
        auto_close_days=14
    )
    session.add(survey)
    session.commit()
    session.refresh(survey)
    return survey


@pytest.fixture
def test_active_survey(session: Session, test_organization: Organization) -> Survey:
    """Create an active test survey."""
    from datetime import datetime
    
    survey = Survey(
        title="Active Test Survey",
        description="An active test survey",
        survey_type=SurveyType.ENPS,
        org_id=test_organization.id,
        status=SurveyStatus.ACTIVE,
        criteria={"nps_required": True},
        activated_at=datetime.utcnow(),
        anonymize_responses=True
    )
    session.add(survey)
    session.commit()
    session.refresh(survey)
    return survey


@pytest.fixture
def test_questions(session: Session) -> list[Question]:
    """Create test questions."""
    questions = [
        Question(
            text="Who do you collaborate with most?",
            question_type=QuestionType.SOCIOMETRIC,
            survey_type=SurveyType.SOCIOMETRY,
            category="collaboration",
            order_index=1,
            options={"max_selections": 3},
            is_active=True
        ),
        Question(
            text="How likely are you to recommend this company?",
            question_type=QuestionType.RATING,
            survey_type=SurveyType.ENPS,
            category="nps",
            order_index=1,
            options={"min_value": 0, "max_value": 10},
            is_active=True
        ),
        Question(
            text="Rate this person's communication skills",
            question_type=QuestionType.RATING,
            survey_type=SurveyType.REVIEW_360,
            category="communication",
            order_index=1,
            options={"min_value": 1, "max_value": 5},
            is_active=True
        )
    ]
    
    for question in questions:
        session.add(question)
    
    session.commit()
    for question in questions:
        session.refresh(question)
    
    return questions


@pytest.fixture
def test_payment(session: Session, test_organization: Organization) -> Payment:
    """Create a test payment."""
    payment = Payment(
        org_id=test_organization.id,
        amount_cents=135000,  # €1350
        currency="EUR",
        team_size=10,
        criteria_count=5,
        status=PaymentStatus.COMPLETED,
        stripe_session_id="cs_test_123",
        stripe_payment_intent_id="pi_test_123",
        metadata={"test": True}
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return payment


@pytest.fixture
def superadmin_token(test_superadmin: User) -> str:
    """Create a JWT token for superadmin."""
    return create_access_token(
        data={"sub": str(test_superadmin.id), "email": test_superadmin.email, "role": test_superadmin.role}
    )


@pytest.fixture
def client_admin_token(test_client_admin: User) -> str:
    """Create a JWT token for client admin."""
    return create_access_token(
        data={"sub": str(test_client_admin.id), "email": test_client_admin.email, "role": test_client_admin.role}
    )


@pytest.fixture
def respondent_token(test_respondent: User) -> str:
    """Create a JWT token for respondent."""
    return create_access_token(
        data={"sub": str(test_respondent.id), "email": test_respondent.email, "role": test_respondent.role}
    )


@pytest.fixture
def auth_headers_superadmin(superadmin_token: str) -> dict:
    """Create authorization headers for superadmin."""
    return {"Authorization": f"Bearer {superadmin_token}"}


@pytest.fixture
def auth_headers_client_admin(client_admin_token: str) -> dict:
    """Create authorization headers for client admin."""
    return {"Authorization": f"Bearer {client_admin_token}"}


@pytest.fixture
def auth_headers_respondent(respondent_token: str) -> dict:
    """Create authorization headers for respondent."""
    return {"Authorization": f"Bearer {respondent_token}"}


# Parametrized fixtures for testing different user roles
@pytest.fixture(params=[
    ("superadmin", "auth_headers_superadmin"),
    ("client_admin", "auth_headers_client_admin"),
])
def admin_auth_headers(request):
    """Parametrized fixture for admin-level authentication headers."""
    return request.getfixturevalue(request.param[1])


@pytest.fixture
def mock_stripe_session():
    """Mock Stripe session for payment testing."""
    return {
        "id": "cs_test_123",
        "url": "https://checkout.stripe.com/pay/cs_test_123",
        "payment_status": "paid",
        "amount_total": 135000,
        "currency": "eur",
        "customer_email": "admin@test.com",
        "payment_intent": "pi_test_123"
    }


@pytest.fixture
def mock_sendgrid_response():
    """Mock SendGrid API response."""
    class MockResponse:
        status_code = 202
        body = "Email sent successfully"
        
    return MockResponse()


# Environment setup for testing
@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-testing-only")
    monkeypatch.setenv("SENDGRID_API_KEY", "test-sendgrid-key")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_test_key")
    monkeypatch.setenv("STRIPE_PUBLISHABLE_KEY", "pk_test_test_key")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")


# Markers for different test categories
pytestmark = [
    pytest.mark.asyncio,
]


# Custom test markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "auth: mark test as authentication related")
    config.addinivalue_line("markers", "api: mark test as API endpoint test")
    config.addinivalue_line("markers", "database: mark test as database operation test")
    config.addinivalue_line("markers", "payments: mark test as payment processing test")
    config.addinivalue_line("markers", "analytics: mark test as analytics related")