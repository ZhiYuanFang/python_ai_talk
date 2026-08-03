## ADDED Requirements

### Requirement: Shared birthday-to-months derivation
The system SHALL provide a shared helper to derive non-negative baby age in whole months from birthday using Asia/Shanghai calendar rules (same semantics as tip `derive_baby_age`). Tip and clinic SHALL use this shared derivation. Missing or unparsable birthday SHALL yield unknown age (not zero).

#### Scenario: Valid birthday yields months
- **WHEN** baby profile contains a valid birthday
- **THEN** clinic and tip compute the same integer months value for the same calendar day

#### Scenario: Missing birthday is unknown
- **WHEN** birthday is absent or unparsable
- **THEN** age months remain unset/unknown and MUST NOT be coerced to 0

### Requirement: Age band for Q&A matching
The system SHALL map months to age_band as: months < 36 → `m{N}`; months >= 36 → `y{Y}` where Y is floor(months/12). Q&A ingest and search SHALL use this band.

#### Scenario: Under three years uses month band
- **WHEN** baby age is 11 months
- **THEN** age_band is `m11`

#### Scenario: Three years and above uses year band
- **WHEN** baby age is 40 months
- **THEN** age_band is `y3`

### Requirement: Clinic prompts use months not raw birthday
Clinic answer prompts SHALL inject derived baby age months (or an explicit unknown label) instead of raw birthday fields when presenting age context to the model.

#### Scenario: Prompt shows months
- **WHEN** clinic builds the answer prompt and months are known
- **THEN** the prompt includes age in months rather than the raw birthday timestamp/string alone
