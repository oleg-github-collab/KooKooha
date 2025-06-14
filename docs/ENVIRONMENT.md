# Environment Variables

Copy `.env.example` to `.env` and adjust the values for your setup.

| Variable | Description |
| --- | --- |
| `APP_NAME` | Application name |
| `APP_VERSION` | Version shown in API responses |
| `DEBUG` | Enable debug mode |
| `ENVIRONMENT` | `production` or `development` |
| `HOST` | Host interface for the server |
| `PORT` | Port for the server |
| `SECRET_KEY` | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime |
| `ALGORITHM` | JWT algorithm |
| `DATABASE_URL` | SQL database URL |
| `ALLOWED_ORIGINS` | CORS origins, comma separated |
| `ALLOWED_METHODS` | CORS methods |
| `ALLOWED_HEADERS` | CORS headers |
| `SENDGRID_API_KEY` | SendGrid API key for email |
| `FROM_EMAIL` | Sender email address |
| `FROM_NAME` | Sender name |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret |
| `OPENAI_API_KEY` | Optional OpenAI API key |
| `OPENAI_MODEL` | OpenAI model name |
| `RATE_LIMIT_REQUESTS` | Requests per rate limit window |
| `RATE_LIMIT_WINDOW` | Rate limit window in seconds |
| `BASE_PRICE_CENTS` | Base package price in cents |
| `PRICE_PER_ADDITIONAL_PERSON_CENTS` | Extra price per person |
| `PRICE_PER_ADDITIONAL_CRITERIA_CENTS` | Extra price per criteria |
| `BASE_TEAM_SIZE` | Team size included in base price |
| `BASE_CRITERIA_COUNT` | Criteria count included in base price |
| `UPLOAD_MAX_SIZE` | Max upload size in bytes |
| `ALLOWED_EXTENSIONS` | Allowed file extensions |
| `LOG_LEVEL` | Logging level |
| `LOG_FILE` | Log file path |
| `LOG_ROTATION` | Log rotation interval |
| `LOG_RETENTION` | Log retention period |
| `FRONTEND_URL` | Base URL of frontend |
| `SURVEY_URL_TEMPLATE` | Template for survey links |
| `SURVEY_TOKEN_EXPIRE_DAYS` | Survey token lifetime |
| `MAX_TEAM_SIZE` | Max number of team members supported |
| `MAX_CRITERIA_COUNT` | Max number of survey criteria supported |
| `SCHEDULER_TIMEZONE` | Time zone for scheduled tasks |
