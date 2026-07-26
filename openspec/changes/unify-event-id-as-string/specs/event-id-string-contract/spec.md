## ADDED Requirements

### Requirement: Event dictionary normalizes IDs as strings

The system SHALL normalize event identity fields to strings when loading the event dictionary from the history service. Specifically, `event_id` and `parent_id` SHALL be strings (empty string when the source value is missing or null). Downstream consumers MUST NOT need to coerce these fields for equality or set membership.

#### Scenario: Numeric id from Go becomes string event_id

- **WHEN** history-service returns an option with `"id": 52` and `"parentId": 10`
- **THEN** the normalized dictionary entry SHALL contain `event_id` equal to `"52"` and `parent_id` equal to `"10"` (both of type string)

#### Scenario: Missing id becomes empty string

- **WHEN** an option lacks `id` or `id` is null
- **THEN** the normalized entry SHALL use `event_id` equal to `""` (string) and MUST NOT use the literal `"None"`

### Requirement: Tip request event_id is string

The tip stream request model SHALL declare `event_id` as a string, aligned with the Go tip client contract.

#### Scenario: Tip request accepts string event_id

- **WHEN** a client POSTs tip stream body with `"event_id": "52"`
- **THEN** validation SHALL succeed and graph state / prompts SHALL observe a string `event_id`

#### Scenario: Tip schema rejects non-coercible event_id types when applicable

- **WHEN** a client sends an `event_id` that cannot be represented as a string identifier under the request model rules
- **THEN** the API SHALL reject the request with a validation error

### Requirement: Data requirement and history filter use string event_ids

Data-requirement judgment and filtered history fetch SHALL treat `event_ids` as a list of strings. Validity checks against the event dictionary SHALL compare in string space. Outbound query parameters to Go MAY still serialize as a comma-separated string.

#### Scenario: Judge keeps only IDs present in dictionary as strings

- **WHEN** the LLM returns `event_ids` that include both valid and invalid IDs (numbers or digit strings)
- **THEN** the node SHALL coerce candidates to strings, retain only IDs present in the dictionary, and store `event_ids` as `List[str]`

#### Scenario: Filtered history receives string event_ids

- **WHEN** `get_filtered_history_events` is called with `event_ids=["1","2"]`
- **THEN** the client SHALL send query `eventIds=1,2` without requiring integer-typed list elements in Python

### Requirement: Vector store and cache compare event_id as string

Event vector store helpers and event dictionary cache change detection SHALL resolve and compare `event_id` values as strings so that `52` and `"52"` are not treated as different events after normalization.

#### Scenario: Cache diff uses string identity

- **WHEN** the previous dictionary and the new dictionary refer to the same logical event whose IDs were normalized to strings
- **THEN** change detection SHALL NOT report that event as both removed and added solely due to int/str mismatch

#### Scenario: Vector helpers stringify resolved event_id

- **WHEN** `_resolve_event_id_name` (or equivalent) reads an event whose `event_id` or legacy `id` is a number
- **THEN** the returned event id SHALL be a string suitable for metadata and where filters
