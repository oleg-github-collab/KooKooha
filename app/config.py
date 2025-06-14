"""Application configuration settings."""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application Settings
    app_name: str = Field(default="Human Lens API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="production", env="ENVIRONMENT")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=30, env="REFRESH_TOKEN_EXPIRE_DAYS")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    
    # Database
    database_url: str = Field(default="sqlite:///./data/human_lens.db", env="DATABASE_URL")
    
    # CORS Settings
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    allowed_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        env="ALLOWED_METHODS"
    )
    allowed_headers: List[str] = Field(default=["*"], env="ALLOWED_HEADERS")
    
    # Email Settings
    sendgrid_api_key: str = Field(env="SENDGRID_API_KEY")
    from_email: str = Field(default="noreply@kookooha.com", env="FROM_EMAIL")
    from_name: str = Field(default="Kookooha Team", env="FROM_NAME")
    
    # Stripe Settings
    stripe_publishable_key: str = Field(env="STRIPE_PUBLISHABLE_KEY")
    stripe_secret_key: str = Field(env="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(env="STRIPE_WEBHOOK_SECRET")
    
    # OpenAI Settings
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")
    
    # Pricing Configuration
    base_price_cents: int = Field(default=75000, env="BASE_PRICE_CENTS")
    price_per_additional_person_cents: int = Field(default=7500, env="PRICE_PER_ADDITIONAL_PERSON_CENTS")
    price_per_additional_criteria_cents: int = Field(default=15000, env="PRICE_PER_ADDITIONAL_CRITERIA_CENTS")
    base_team_size: int = Field(default=4, env="BASE_TEAM_SIZE")
    base_criteria_count: int = Field(default=2, env="BASE_CRITERIA_COUNT")
    
    # File Storage
    upload_max_size: int = Field(default=10485760, env="UPLOAD_MAX_SIZE")  # 10MB
    allowed_extensions: List[str] = Field(default=["csv", "xlsx", "json"], env="ALLOWED_EXTENSIONS")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", env="LOG_FILE")
    log_rotation: str = Field(default="1 day", env="LOG_ROTATION")
    log_retention: str = Field(default="30 days", env="LOG_RETENTION")
    
    # Frontend URLs
    frontend_url: str = Field(default="https://kookooha.com", env="FRONTEND_URL")
    survey_url_template: str = Field(
        default="https://kookooha.com/survey/{token}",
        env="SURVEY_URL_TEMPLATE"
    )
    
    # Survey Settings
    survey_token_expire_days: int = Field(default=30, env="SURVEY_TOKEN_EXPIRE_DAYS")
    max_team_size: int = Field(default=1000, env="MAX_TEAM_SIZE")
    max_criteria_count: int = Field(default=50, env="MAX_CRITERIA_COUNT")
    
    # Scheduler Settings
    scheduler_timezone: str = Field(default="Europe/Berlin", env="SCHEDULER_TIMEZONE")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> any:
            """Parse environment variables, handling lists."""
            if field_name in ["allowed_origins", "allowed_methods", "allowed_headers", "allowed_extensions"]:
                return [item.strip() for item in raw_val.split(",")]
            return cls.json_loads(raw_val)
    
    def calculate_price(self, team_size: int, criteria_count: int) -> int:
        """Calculate total price in cents based on team size and criteria count."""
        additional_people = max(0, team_size - self.base_team_size)
        additional_criteria = max(0, criteria_count - self.base_criteria_count)
        
        total_price = (
            self.base_price_cents +
            (additional_people * self.price_per_additional_person_cents) +
            (additional_criteria * self.price_per_additional_criteria_cents)
        )
        
        return total_price


# Global settings instance
settings = Settings()
