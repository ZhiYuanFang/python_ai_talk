## ADDED Requirements

### Requirement: Care-alert history uses compact two-day lines
Care-alert analyze prompts SHALL inject feeding/care history as compact lines covering only Shanghai calendar today and yesterday, not full JSON. Each line SHALL be `{relativeStartTime}{eventName}{suffix}` where suffix is duration seconds for timer events, `eventNumber` for count events, or the Chinese word `一次` for one-shot events. Relative Chinese time formatting SHALL be used for startTime (e.g. 刚刚 / N分钟前 / 今天 HH:mm / 昨天 HH:mm). History lines MUST NOT include eventId.

#### Scenario: Compact lines for mixed event types
- **WHEN** care-alert builds the user message with timer, count, and one-shot events from today or yesterday
- **THEN** the history block uses compact lines with the corresponding suffixes and relative start times
- **AND** no history line contains an eventId

#### Scenario: Older days excluded from prompt
- **WHEN** history_events include records from before yesterday (Shanghai)
- **THEN** those records are not included in the compact history block

### Requirement: Separate eventName to eventId legend
When event ids are available, care-alert prompts SHALL include a separate short legend mapping distinct eventName to eventId for LLM to fill `eventId` in JSON output. The legend MUST NOT be inlined into each history line.

#### Scenario: Legend lists name equals id
- **WHEN** compact history is built and events have eventIds
- **THEN** the prompt includes a separate name-to-id block (e.g. `哺乳=12`)
- **AND** history lines remain without ids

### Requirement: Care-alert fetch window is last two days
Care-alert analyze data preparation SHALL request history for approximately the last two calendar days (yesterday 00:00 Shanghai through now), not a seven-day default window.

#### Scenario: Analyze uses two-day range
- **WHEN** care-alert analyze starts data preparation
- **THEN** its data_requirement time_range targets the last two days (e.g. last_2_days)

### Requirement: Care-alert knowledge uses global top_k
Care-alert analyze SHALL inject qualified mother_baby_knowledge using the same global `knowledge_prompt_top_k` (default 1) and score/quality gates as clinic/tip. It MUST NOT set a care-alert-only higher top_k override.

#### Scenario: Same cap as clinic
- **WHEN** care-alert runs vector search and filtering
- **THEN** at most `knowledge_prompt_top_k` hits are retained for prompt/flywheel ids
- **AND** no care-alert-specific top_k override is applied
