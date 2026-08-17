## ADDED Requirements

### Requirement: Care-alert user message carries runtime data only
Care-alert analyze user messages SHALL include runtime instance fields (baby age line, sex, logic day, recent aggregated history block, event name↔id legend, and optional orchestration history summary when present). The user message MUST NOT restate the full set of judgment policies that already appear in the persisted system `output_format` (min-one when history+legend usable, empty-list conditions, contrastive-example handling, eventId legend rules, non-diagnostic stance). A single short pointer that the model must follow the system judgment and JSON format is allowed.

#### Scenario: User message without duplicated policy paragraph
- **WHEN** care-alert builds the user message for an analyze turn
- **THEN** the message includes age, logic day, and history/legend blocks as applicable
- **AND** it does not contain a long instructional paragraph that repeats system min-one / empty-list / contrastive-example / eventId policies

### Requirement: Care-alert system output_format is the sole compressed policy source
The default persisted care-alert `output_format` SHALL be the sole source of static judgment and JSON output rules for analyze. It MUST use「近期记录」wording (not locking the window to today/yesterday only), MUST retain: min-one when recent history and legend are usable, empty items only when history empty or legend cannot supply eventId, age participation without fabricating unknown age, no invented knowledge-base citations, eventId from legend, contrastive examples as global tone not current-baby facts, and JSON-only output schema. Duplicate restatements between a separate「判定依据」list and a trailing「规则」list MUST be merged so each hard rule appears once. Document version migration SHALL refresh `output_format` while preserving `contrastive_examples`.

#### Scenario: Bootstrap or migrate uses compressed recent-history wording
- **WHEN** the care-alert prompt document is bootstrapped or migrated to the new document version
- **THEN** `output_format` describes recent history (近期) without requiring only today and yesterday
- **AND** min-one and empty-list rules remain present once
- **AND** existing contrastive_examples are preserved on migrate

#### Scenario: Flywheel rejects history instance lines under new label
- **WHEN** a prompt write embeds a concrete「近期记录」instance transcript in place of runtime injection
- **THEN** validation rejects the document
