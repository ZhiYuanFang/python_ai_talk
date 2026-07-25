## ADDED Requirements

### Requirement: Initialize events from normalized dictionary fields
When initializing the feeding event vector store from an event dictionary, the system SHALL read event identity and name from `event_id` / `event_name`, falling back to `id` / `name` when the preferred keys are absent.

#### Scenario: Normalized dictionary events are ingested
- **WHEN** `initialize_events` receives events shaped like `{"event_id": 52, "event_name": "站练习", ...}`
- **THEN** the system SHALL add standard vector entries for those events and SHALL NOT log them as invalid solely due to missing `id` / `name`

#### Scenario: Legacy id/name dictionary still works
- **WHEN** `initialize_events` receives events shaped like `{"id": 52, "name": "站练习"}`
- **THEN** the system SHALL still add standard vector entries for those events

#### Scenario: Truly incomplete events are skipped with a clear warning
- **WHEN** an event lacks both `event_id` and `id`, or lacks both `event_name` and `name`
- **THEN** the system SHALL skip that event and SHALL emit a warning that indicates missing identity or name fields

### Requirement: Sync events uses the same field resolution
When synchronizing added or modified events into the feeding event vector store, the system SHALL resolve event identity and name using the same `event_id`/`event_name` with `id`/`name` fallback rules as initialization.

#### Scenario: Added event with event_id is synced
- **WHEN** `sync_events` processes an added event containing `event_id` and `event_name`
- **THEN** the system SHALL write standard entries keyed by that event identity (not empty id/name)
