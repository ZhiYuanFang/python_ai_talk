## ADDED Requirements

### Requirement: History plus qualified knowledge decide care alerts
Care-alert analyze SHALL instruct the LLM to use recent feeding/care history as factual signals and, when present, qualified mother-baby knowledge snippets to calibrate whether an item is worth surfacing. The system SHALL NOT invent knowledge citations. When knowledge is empty after retrieval filters, the model MAY judge from history alone cautiously or return an empty items list; accuracy SHALL take priority over filling the list.

#### Scenario: Both history and knowledge present
- **WHEN** analyze has non-empty history_events and non-empty filtered knowledge
- **THEN** the care-alert prompts require using both to decide whether to emit each留意 item

#### Scenario: No qualifying knowledge
- **WHEN** vector retrieval yields no knowledge above similarity/quality thresholds
- **THEN** the prompt knowledge block is empty or explicitly「无」
- **AND** prompts forbid fabricating knowledge grounds and forbid stuffing unrelated knowledge

### Requirement: Do not force-inject unqualified knowledge
When `search_vectors` (or equivalent) leaves `knowledge` empty due to score/quality filters, care-alert analyze MUST NOT replace it with orchestration `kg_context` (or similar) as if it were qualified retrieved knowledge for flywheel or grounding.

#### Scenario: Empty retrieval stays empty
- **WHEN** filtered knowledge is empty and request carries kg_context
- **THEN** analyze does not copy kg_context into the knowledge list used for prompting and flywheel ids

### Requirement: Persist suggestion to knowledge_ids mapping
After analyze produces items with `suggestionId` values, the system SHALL persist a mapping from each `suggestionId` to the knowledge document ids that were injected into that analyze turn’s prompt (`extract_knowledge_ids`). Mapping TTL SHALL be at least several days (default 7). Missing knowledge ids SHALL still create a mapping with an empty list or skip write; either way feedback MUST remain non-fatal.

#### Scenario: Analyze writes mapping for each suggestion
- **WHEN** analyze returns one or more items each with suggestionId and the turn used knowledge ids [A,B]
- **THEN** each suggestionId can be resolved to knowledge ids including A and B (or the recorded list for that turn)

#### Scenario: Analyze with empty knowledge
- **WHEN** analyze completes with empty knowledge
- **THEN** feedback for those suggestionIds does not update quality scores (no ids) and still returns ok

### Requirement: Fixed-intent feedback updates knowledge quality
`POST /v1/care-alert/feedback` with `intent=follow_up` SHALL apply positive knowledge quality updates to mapped ids; `intent=ignore` SHALL apply negative updates. The handler SHALL return ok on success and MUST NOT fail the HTTP contract when mapping is missing or a single id update fails (log and continue). Free-text NLP SHALL NOT be required.

#### Scenario: follow_up raises quality
- **WHEN** feedback intent is follow_up and mapping has knowledge ids
- **THEN** each id receives a positive update equivalent to clinic helpful feedback

#### Scenario: ignore lowers quality
- **WHEN** feedback intent is ignore and mapping has knowledge ids
- **THEN** each id receives a negative quality update

#### Scenario: Missing mapping still ACKs
- **WHEN** suggestion_id has no mapping
- **THEN** response is ok=true and no quality update is required
