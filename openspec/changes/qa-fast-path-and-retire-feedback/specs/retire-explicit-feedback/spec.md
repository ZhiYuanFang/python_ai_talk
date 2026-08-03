## ADDED Requirements

### Requirement: Implicit acceptance is the only feedback path for tip and clinic
Python tip and clinic APIs SHALL drive knowledge quality updates solely via multi-turn implicit suggestion acceptance. Explicit thumbs-up/down feedback endpoints SHALL NOT be offered.

#### Scenario: Clinic request without explicit feedback still updates quality on accept
- **WHEN** a later clinic turn implicitly marks the prior suggestion as accepted
- **THEN** knowledge quality scores are updated without calling any `/feedback` endpoint

## REMOVED Requirements

### Requirement: Clinic explicit feedback API
**Reason**: Product removed thumbs UI; main path is implicit acceptance; `answer_id` often does not map to knowledge chunk ids.
**Migration**: Rely on clinic graph implicit feedback; remove Go/Flutter callers of `/clinic/feedback` and `/v1/clinic/feedback`.

#### Scenario: Endpoint removed
- **WHEN** a client POSTs to `/v1/clinic/feedback`
- **THEN** the route is not registered (HTTP 404)

### Requirement: Tip explicit feedback API
**Reason**: Same as clinic; tip flywheel/quality follows implicit or other non-explicit paths as designed elsewhere.
**Migration**: Remove Go/Flutter callers of `/tip/feedback` and `/v1/tip/feedback`.

#### Scenario: Endpoint removed
- **WHEN** a client POSTs to `/v1/tip/feedback`
- **THEN** the route is not registered (HTTP 404)
