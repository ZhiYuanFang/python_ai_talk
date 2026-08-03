## ADDED Requirements

### Requirement: Standalone question rewrite for QA retrieval
Clinic SHALL rewrite the current multi-turn user question into a standalone question before searching the Q&A fast-path store. The same rewrite SHALL be used as the ingest key when promoting an accepted answer. If rewrite fails or times out, the system SHALL treat the turn as a fast-path miss and MUST NOT fall back to the raw user text for Q&A search.

#### Scenario: Rewrite succeeds then search uses standalone question
- **WHEN** clinic continues a multi-turn session and the rewrite LLM returns a standalone question within the timeout
- **THEN** Q&A search uses that standalone question as the query key

#### Scenario: Rewrite failure is a miss
- **WHEN** rewrite fails or exceeds the configured timeout (default 2s)
- **THEN** clinic does not search Q&A with the raw query and continues the normal prepare path

### Requirement: Global Q&A hit skips full clinic prepare
The system SHALL maintain a global Q&A vector store with age-band metadata. Clinic SHALL return a stored answer and skip the remainder of the prepare/reasoning chain when similarity exceeds 0.8, Q&A quality_score is at least 0.7, and age_band matches the current baby. Unknown baby age SHALL NOT produce a hit.

#### Scenario: Qualified hit ends early
- **WHEN** rewritten question finds a Q&A entry with similarity > 0.8, quality_score >= 0.7, and matching age_band
- **THEN** clinic returns that answer without running the remaining data-requirement / history / full clinic_answer prepare chain

#### Scenario: Unknown age never hits
- **WHEN** baby birthday is missing or age months cannot be derived
- **THEN** clinic does not take the Q&A fast path

#### Scenario: Similarity or quality below threshold continues prepare
- **WHEN** best Q&A candidate fails similarity, quality, or age_band checks
- **THEN** clinic continues the normal prepare path

### Requirement: Promote accepted answers into Q&A store
The system SHALL upsert a Q&A entry only when implicit acceptance is `accepted` and a successful standalone rewrite exists for that turn. Entries SHALL be global (not device-scoped) and include age_band derived from baby months.

#### Scenario: Accepted with rewrite promotes
- **WHEN** implicit feedback marks the prior suggestion accepted and that turn has a successful standalone question
- **THEN** the system stores standalone_question, answer, age_band, and quality metadata in the global Q&A store

#### Scenario: Accepted without rewrite skips promote
- **WHEN** acceptance is true but standalone rewrite was unavailable that turn
- **THEN** the system does not write a Q&A fast-path entry

### Requirement: Block fast path for history and sensitive cases
Clinic SHALL NOT take the Q&A fast path when `force_needs_history` is true, the request is a history point-query, or the question is classified as blocked sensitive medical content for fast-path reuse.

#### Scenario: force_needs_history forces miss
- **WHEN** clinic state has force_needs_history true
- **THEN** Q&A fast path is skipped and prepare continues
