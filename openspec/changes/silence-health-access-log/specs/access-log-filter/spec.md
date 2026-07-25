## ADDED Requirements

### Requirement: Health check access logs are silenced
The system SHALL NOT emit uvicorn access log records for HTTP requests whose path is `/v1/health`.

#### Scenario: Health probe does not appear in access log
- **WHEN** a client issues `GET /v1/health`
- **THEN** no access log line for that request SHALL be written by `uvicorn.access`

#### Scenario: Health probe still returns successfully
- **WHEN** a client issues `GET /v1/health`
- **THEN** the endpoint SHALL still return a successful health response (behavior and payload unchanged)

### Requirement: Non-health access logs are preserved
The system SHALL continue to emit uvicorn access log records for HTTP requests that are not health checks.

#### Scenario: Business API access log remains
- **WHEN** a client issues a request to a non-health API path (for example under `/v1/analyze`, `/v1/clinic`, `/v1/tip`, or `/v1/knowledge`)
- **THEN** an access log line for that request SHALL still be written by `uvicorn.access`

### Requirement: Filter applies on all app entrypoints
The access-log filter SHALL be active whenever the FastAPI application module is loaded, including both `python -m app.main` and Docker `uvicorn app.main:app` startup paths.

#### Scenario: Module import installs the filter
- **WHEN** `app.main` is imported by uvicorn
- **THEN** the health-path filter SHALL be attached to the `uvicorn.access` logger before the service accepts traffic
