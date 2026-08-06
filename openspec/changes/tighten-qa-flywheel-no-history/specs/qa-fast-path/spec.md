## MODIFIED Requirements

### Requirement: Promote accepted answers into Q&A store
The system SHALL upsert a Q&A entry only when all of the following hold: implicit acceptance is `accepted`; a successful standalone rewrite exists for that turn; and that turn was **not** history-grounded (`history_grounded` is false / `needs_history` was false). Entries SHALL be global (not device-scoped) and include age_band derived from baby months. When `history_grounded` is true or unknown/missing, the system MUST NOT promote.

#### Scenario: Accepted with rewrite promotes when not history-grounded
- **WHEN** implicit feedback marks the prior suggestion accepted, that turn has a successful standalone question, and `history_grounded` is false
- **THEN** the system stores standalone_question, answer, age_band, and quality metadata in the global Q&A store

#### Scenario: Accepted without rewrite skips promote
- **WHEN** acceptance is true but standalone rewrite was unavailable that turn
- **THEN** the system does not write a Q&A fast-path entry

#### Scenario: Accepted but history-grounded skips promote
- **WHEN** acceptance is true and rewrite exists but `history_grounded` is true
- **THEN** the system does not write a Q&A fast-path entry

#### Scenario: Missing history_grounded is conservative
- **WHEN** acceptance is true and rewrite exists but `history_grounded` is missing from session metadata
- **THEN** the system does not write a Q&A fast-path entry

### Requirement: Block fast path for history and sensitive cases
Clinic SHALL NOT take the Q&A fast path when any of the following hold: `force_needs_history` is true; the request is a history point-query; the question is classified as blocked sensitive medical content for fast-path reuse; or the current turn's implicit judgment of the previous suggestion is `rejected` (`block_fast_path` or equivalent).

#### Scenario: force_needs_history forces miss
- **WHEN** clinic state has force_needs_history true
- **THEN** Q&A fast path is skipped and prepare continues

#### Scenario: Rejected previous suggestion forces miss
- **WHEN** implicit feedback classifies the prior suggestion as `rejected`
- **THEN** Q&A fast path is skipped for the current turn and prepare/generation continues without returning a cached Q&A answer

## ADDED Requirements

### Requirement: Demote Q&A quality when a fast-path answer is rejected
When implicit feedback is `rejected` and the prior suggestion recorded a non-empty `qa_match_id`, the system SHALL decrease that Q&A entry's quality_score (same direction as negative knowledge feedback). Missing or unknown ids SHALL NOT abort the main flow.

#### Scenario: Reject after QA hit lowers quality
- **WHEN** the prior turn was a Q&A fast-path hit with `qa_match_id` set and the user rejects it
- **THEN** the system updates that Q&A document's quality_score downward

#### Scenario: Reject without qa_match_id skips QA demotion
- **WHEN** rejection occurs but `qa_match_id` is empty
- **THEN** the system does not attempt Q&A quality update for that reason and continues
