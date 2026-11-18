## MODIFIED Requirements

### Requirement: Filter applies on all app entrypoints

The access-log filter SHALL be active whenever a FastAPI application module that serves `/v1/health` is loaded. This includes `app.main`（`python -m app.main` / `uvicorn app.main:app`）and `prediction.main`（`uvicorn prediction.main:app` / Docker python-prediction）。The health-path filter SHALL be attached to the `uvicorn.access` logger before the service accepts traffic.

#### Scenario: Module import installs the filter on talk

- **WHEN** `app.main` is imported by uvicorn
- **THEN** the health-path filter SHALL be attached to the `uvicorn.access` logger before the service accepts traffic

#### Scenario: Module import installs the filter on prediction

- **WHEN** `prediction.main` is imported by uvicorn
- **THEN** the health-path filter SHALL be attached to the `uvicorn.access` logger before the service accepts traffic

#### Scenario: Prediction health probe does not appear in access log

- **WHEN** a client issues `GET /v1/health` against python-prediction
- **THEN** no access log line for that request SHALL be written by `uvicorn.access`
- **AND** the endpoint SHALL still return a successful health response
