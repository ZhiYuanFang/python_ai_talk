## ADDED Requirements

### Requirement: At least one care-alert item when recent history is usable
When care-alert analyze has non-empty compact recent history (last two days) and a non-empty event name↔id legend sufficient to fill `eventId`, the system SHALL return at least one item in `items`. When history is empty or no reliable legend exists, the system MAY return an empty `items` list.

#### Scenario: History and legend present yields non-empty items
- **WHEN** analyze completes with usable last-two-days history_events and a non-empty event id legend
- **THEN** the response `items` array contains at least one element
- **AND** each returned item includes a valid `eventId` from that legend

#### Scenario: No history allows empty items
- **WHEN** analyze has no usable last-two-days history (compact history empty or equivalent「无」)
- **THEN** `items` MAY be empty

#### Scenario: History without legend allows empty items
- **WHEN** history exists but no event name↔id legend can be built
- **THEN** `items` MAY be empty rather than inventing `eventId` values

### Requirement: Baby age must drive care-alert judgment
Care-alert prompting and any deterministic fallback item SHALL incorporate baby age months when known. The model instructions MUST require choosing and phrasing留意 points in light of age. When age is unknown, the system MUST NOT fabricate a specific age or age-norm statistics; it MAY still emit an item if history+legend rules require one, with age left unspecified.

#### Scenario: Known age appears in runtime prompt
- **WHEN** `baby_age_months` is a known integer for the analyze turn
- **THEN** the user (runtime) prompt includes that age
- **AND** system/bootstrap rules require using that age when deciding whether and how to surface items

#### Scenario: Fallback item carries age when known
- **WHEN** a deterministic fallback item is synthesized because the LLM returned empty items despite usable history and legend, and age is known
- **THEN** the fallback item’s reasons include `ageMonths` equal to that known age (or equivalent field)
- **AND** the summary does not invent unrelated age-norm claims

#### Scenario: Unknown age does not invent norms
- **WHEN** baby age is unknown and an item is still produced under the history rules
- **THEN** the system does not invent a concrete month age or fake median/expectation numbers solely from age norms

### Requirement: Prompt and bootstrap align with min-one and age rules
The bootstrapped local `output_format` and the runtime user guidance for care-alert SHALL instruct that usable recent history requires at least one item, that empty `items` is only for no-history or no-legend cases, and that baby age must be considered. Guidance that tells the model to return empty `items` whenever history is merely “unclear” MUST NOT remain as the primary rule when history+legend are usable.

#### Scenario: User guidance no longer prefers empty on unclear history alone
- **WHEN** building the care-alert user message for a turn with history
- **THEN** the guidance does not primarily tell the model to return empty items solely because history is unclear
- **AND** it requires at least one item when history and legend are usable, considering baby age

### Requirement: Deterministic fallback when LLM returns empty
If after LLM generation and normalization `items` is empty while usable last-two-days history and a non-empty legend exist, the system SHALL synthesize at least one soft care-alert item from history (valid `eventId` from the legend, non-diagnostic tone) so the min-one rule holds without inventing knowledge-base citations.

#### Scenario: Empty LLM output gets one soft item
- **WHEN** the LLM returns no usable items and history+legend are usable
- **THEN** analyze still returns at least one normalized item with suggestionId, eventId, summaryLine, followUpPrompt, and reasons
