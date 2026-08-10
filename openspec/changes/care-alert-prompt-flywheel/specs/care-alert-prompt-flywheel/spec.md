## ADDED Requirements

### Requirement: Care-alert analyze does not use knowledge retrieval
Care-alert analyze SHALL NOT call vector knowledge retrieval (`search_vectors` or equivalent) and SHALL NOT inject mother-baby knowledge snippets or orchestration `kg_context` into the LLM prompt used to decide留意 items. Decisions SHALL be based on recent history signals, baby age (when known), output-format rules, and any persisted contrastive feedback examples.

#### Scenario: Graph skips knowledge search
- **WHEN** a care-alert analyze request is executed
- **THEN** the care-alert graph path does not invoke knowledge vector search for that request

#### Scenario: kg_context is not prompt ground truth
- **WHEN** the request carries `kg_context` and filtered knowledge would have been empty
- **THEN** analyze does not treat `kg_context` as qualified knowledge in the prompt

### Requirement: Load global prompt from local volume directory
The system SHALL load the global care-alert prompt projection from a configured local directory (default under `/app/data/care_alert`, intended to be a Docker bind/volume). The directory path SHALL be configurable via environment settings consistent with env-config naming (no `PYTHON_AI_TALK_` prefix).

#### Scenario: Existing prompt file is used
- **WHEN** the configured directory contains a valid `prompt.json` (or equivalent agreed filename)
- **THEN** analyze uses that file’s static prompt blocks for the LLM system (or equivalent) content

#### Scenario: Missing file bootstraps default
- **WHEN** the prompt file is missing at startup or first analyze
- **THEN** the system writes a default template into the directory and uses that template
- **AND** the default template includes output-format rules and does not embed a concrete baby age or a concrete history transcript

### Requirement: Dynamic age and history are runtime-only
Baby age and recent history (and event-id legend derived from history) MUST be supplied at request render time. Persisted prompt files MUST NOT store per-request age values or history transcripts as frozen instance text. After any flywheel rewrite, the system MUST reject or refuse to persist a prompt that embeds such instance values in place of runtime injection.

#### Scenario: Two analyzes differ in age and history
- **WHEN** two analyze calls have different `baby_age_months` and different history_events
- **THEN** each call’s user-facing prompt content reflects that call’s age and history
- **AND** the on-disk prompt projection is not required to change between the two calls solely due to those dynamic fields

#### Scenario: Flywheel cannot freeze dynamic fields
- **WHEN** a flywheel rewrite would write concrete age or history transcript into the persisted prompt file
- **THEN** the system does not replace the previous valid prompt with that invalid content

### Requirement: Initial prompt composition and flywheel examples block
The bootstrapped prompt SHALL include output-format (and hard JSON/schema rules). After feedback-driven updates, the persisted prompt MAY additionally include a bounded user-feedback contrastive-examples block. Analyze SHALL include that examples block when non-empty.

#### Scenario: Fresh install has no examples
- **WHEN** only the bootstrap prompt exists
- **THEN** analyze still runs with output format plus runtime age and history
- **AND** contrastive examples are empty or explicitly absent

#### Scenario: After flywheel update examples appear
- **WHEN** the prompt file contains a non-empty contrastive-examples section within the configured size limit
- **THEN** analyze includes that section for the LLM as global guidance (not as this baby’s records)

### Requirement: Persist suggestion snapshot for feedback attribution
After analyze produces items with `suggestionId` values, the system SHALL persist a short-lived mapping from each `suggestionId` to a snapshot of that item sufficient for feedback attribution (at least event identity and reason-type / signal strength summary). Mapping TTL SHALL be at least several days (default 7). The mapping MUST NOT be required to include knowledge document ids.

#### Scenario: Analyze writes snapshot per suggestion
- **WHEN** analyze returns one or more items each with suggestionId
- **THEN** each suggestionId can be resolved to a non-knowledge snapshot for feedback handling

### Requirement: Fixed-intent feedback drives prompt flywheel not knowledge scores
`POST /v1/care-alert/feedback` with `intent=follow_up` or `intent=ignore` SHALL record feedback against the suggestion snapshot into a durable local ledger under the care-alert data directory and SHALL NOT update `mother_baby_knowledge` quality scores for care-alert. The handler MUST return ok when mapping is missing or flywheel side effects fail (log and continue). Free-text NLP SHALL NOT be required.

#### Scenario: follow_up and ignore append ledger
- **WHEN** feedback arrives with a valid suggestion snapshot and intent follow_up or ignore
- **THEN** a ledger entry is recorded for later aggregation
- **AND** no care-alert path calls knowledge quality score updates

#### Scenario: Missing mapping still ACKs
- **WHEN** suggestion_id has no mapping
- **THEN** response is ok=true and prompt rewrite is not required

### Requirement: Contrastive examples for conflicting similar feedback
When aggregating feedback for the global prompt, the system SHALL represent conflicting outcomes for similar suggestion types as contrastive examples (positive vs negative vs explicit tension), and MUST NOT collapse opposite intents for the same type into a single net-score slogan that erases the conflict.

#### Scenario: Same type opposite intents retained
- **WHEN** the ledger contains both follow_up and ignore for the same reason type (or event class) under different signal-strength bands
- **THEN** the rendered contrastive-examples block preserves both “prefer surface” and “prefer suppress” guidance (or an explicit tension line)
- **AND** does not keep only the majority vote as the sole line for that type

### Requirement: Bound examples length and rewrite safely
The contrastive-examples section written into the prompt file MUST NOT grow without bound. The system SHALL enforce a configured maximum size for that section, aggregate by type/signal slots, and rewrite the prompt file atomically (and with locking sufficient for concurrent writers on the same volume). Low-evidence slots MAY be omitted.

#### Scenario: Oversized draft is not persisted
- **WHEN** a rewrite produces contrastive-examples text exceeding the configured maximum
- **THEN** the system truncates, re-aggregates, or aborts the write so the persisted section stays within the limit
- **AND** a previously valid prompt file remains usable if the write is aborted

#### Scenario: Restart keeps prompt
- **WHEN** the process restarts and the Docker volume still contains the prompt file
- **THEN** analyze loads the same persisted prompt projection (including examples if present)
