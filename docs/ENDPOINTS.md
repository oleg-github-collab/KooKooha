# API Overview

The API follows REST principles and is documented via OpenAPI at `/docs` when the server is running.

## Public Endpoints

- `GET /health` – Service health check
- `GET /` – API root information

## Authentication

- `POST /api/v1/auth/register` – Register organization and admin user
- `POST /api/v1/auth/login` – Obtain access and refresh tokens
- `POST /api/v1/auth/refresh` – Refresh an expired access token
- `GET /api/v1/auth/me` – Current user details
- `POST /api/v1/auth/logout` – Revoke refresh token

## Organizations

- `GET /api/v1/organizations/{org_id}` – Organization info
- `PUT /api/v1/organizations/{org_id}` – Update organization
- `GET /api/v1/organizations/{org_id}/members` – List team members
- `POST /api/v1/organizations/{org_id}/team/import` – Import team from JSON/CSV

## Surveys

- `POST /api/v1/surveys` – Create survey
- `GET /api/v1/surveys` – List surveys
- `POST /api/v1/surveys/{id}/activate` – Activate survey
- `POST /api/v1/surveys/{id}/invite` – Send invitations

## Responses

- `POST /api/v1/responses/submit` – Submit survey responses
- `GET /api/v1/responses/{survey_id}` – List responses
- `GET /api/v1/responses/{survey_id}/analytics` – Aggregated metrics

## Payments

- `POST /api/v1/payments/calculate` – Calculate pricing
- `POST /api/v1/payments/checkout` – Create Stripe checkout session
- `POST /api/v1/payments/webhook` – Stripe webhook endpoint

## Admin

Admin routes require a superadmin token.

- `GET /api/v1/admin/stats` – Platform statistics
- `GET /api/v1/admin/organizations` – Manage organizations
- `GET /api/v1/admin/users` – Manage users
- `GET /api/v1/admin/surveys` – Manage surveys
