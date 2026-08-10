## ADDED Requirements

### Requirement: Care-alert prompt directory env is unprefixed and consistent
The care-alert prompt/ledger directory SHALL be configurable via an unprefixed environment variable (e.g. `CARE_ALERT_PROMPT_DIR`) that is consistent across `.env`, docker-compose injection, and Python `settings` (pydantic env mapping). Optional flywheel knobs (examples max size, rewrite batch size) SHALL follow the same unprefixed naming rule when exposed.

#### Scenario: Default and override
- **WHEN** `CARE_ALERT_PROMPT_DIR` is unset
- **THEN** the application uses the documented default path suitable for the container mount (e.g. `/app/data/care_alert` or project-relative `data/care_alert` in local runs)
- **WHEN** `CARE_ALERT_PROMPT_DIR` is set in the env file and injected by compose
- **THEN** Python settings read the same value without a `PYTHON_AI_TALK_` prefix

#### Scenario: Deploy guide lists the variable
- **WHEN** an operator consults the environment variable inventory in deploy documentation
- **THEN** `CARE_ALERT_PROMPT_DIR` (and any exposed related knobs) appear without `PYTHON_AI_TALK_` prefixes
