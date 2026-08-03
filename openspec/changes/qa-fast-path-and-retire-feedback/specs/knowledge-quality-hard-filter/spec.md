## ADDED Requirements

### Requirement: Hard-filter knowledge by quality_score
General knowledge retrieval SHALL exclude documents whose `quality_score` is below the configured minimum (default 0.7). Documents missing `quality_score` SHALL be treated as the store default (currently 0.8) for filter purposes.

#### Scenario: Low-quality chunks excluded
- **WHEN** knowledge search returns candidates including one with quality_score 0.5 and one with 0.9
- **THEN** only candidates with quality_score >= 0.7 are passed to the answer prompt

#### Scenario: Default score passes filter
- **WHEN** a knowledge document has no explicit quality_score and the store default is 0.8
- **THEN** that document is eligible for retrieval under the default minimum of 0.7
