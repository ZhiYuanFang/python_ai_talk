## ADDED Requirements

### Requirement: Care-alert prompt data volume is mounted
Baseline `docker-compose.yml` for python-ai-talk SHALL bind-mount a host (or named) care-alert data directory to the container path used for the global care-alert prompt and feedback ledger (default `/app/data/care_alert`). This volume SHALL be independent of the Chroma persist directory and SHALL NOT mount an empty host models directory over `/app/data/models`.

#### Scenario: Compose lists care-alert data mount
- **WHEN** an operator inspects baseline `docker-compose.yml` volumes for the python-ai-talk service
- **THEN** there is a mount whose container path is the configured care-alert prompt directory (default `/app/data/care_alert`)
- **AND** the Chroma persist mount remains present as before

#### Scenario: Prompt survives container recreate
- **WHEN** the care-alert prompt file was written under the mounted directory and the container is recreated with the same volume
- **THEN** the prompt file is still available at the mounted container path
