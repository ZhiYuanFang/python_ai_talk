## MODIFIED Requirements

### Requirement: Care-alert history uses compact two-day lines
Care-alert analyze prompts SHALL inject feeding/care history as compact aggregated lines, not full JSON. History SHALL be aggregated by Shanghai calendar day and `eventName` into lines of the form `{dayLabel}·{eventName}·{clockList}·{totalSegment}` where:

- `dayLabel` is a calendar date relative to the prompt logic day (or Shanghai "now" when logic day is absent): `MM-DD` when the event year equals the anchor year, otherwise `YYYY-MM-DD`
- `dayLabel` MUST NOT be the relative words `今天` or `昨天`
- `clockList` is each occurrence's start time as `HH:MM`, ordered ascending by startTime within the group, joined by `/`
- `totalSegment` depends on event type (`number` | `time` | `one`):
  - **time**: sum of valid durations, total seconds converted to minutes with round-half-up, rendered as `总时长XhYm` (omit `0h` when hours are zero; if no valid duration, `总时长0m`)
  - **number**: `总量{sumOfEventNumber}{unit}` where unit is taken from the first non-empty `eventUnit` / `event_unit` / `unit` in the group (omit unit suffix when empty)
  - **one**: `{occurrenceCount}次`

The compact builder MUST NOT drop events solely because they fall outside today/yesterday; any event with a parseable Shanghai calendar day in the provided `history_events` SHALL be eligible for aggregation (fetch window remains the caller's responsibility). Events with no parseable date MUST be omitted. Within the same calendar day, lines SHALL be ordered by `eventName`. Across days, lines SHALL be ordered by calendar date descending (newest day first). Relative Chinese phrases such as `刚刚` / `N分钟前` MUST NOT be used in these aggregated lines. History lines MUST NOT include eventId.

#### Scenario: Aggregated line for timer events
- **WHEN** care-alert builds the user message and the same eventName occurs multiple times on one calendar day as timer events with valid start/end
- **THEN** one line is emitted for that day and name with ascending `HH:MM` clocks and a `总时长XhYm` total
- **AND** the history line does not contain an eventId

#### Scenario: Aggregated line for count events with unit
- **WHEN** care-alert builds history for count events sharing a name on one calendar day with eventNumber values and an eventUnit
- **THEN** the line uses `总量` equal to the sum of eventNumber followed by that unit
- **AND** clocks are listed as `HH:MM` joined by `/`

#### Scenario: One-shot events use occurrence count
- **WHEN** care-alert aggregates one-shot events for a name on one calendar day
- **THEN** the total segment is `{N}次` where N is the number of occurrences that day

#### Scenario: Days older than yesterday are included when present
- **WHEN** history_events include records from before yesterday (Shanghai) with parseable dates
- **THEN** those records are included in the compact history block with calendar dayLabel

#### Scenario: Same-year day label omits year
- **WHEN** an event date is in the same calendar year as the logic-day anchor
- **THEN** dayLabel is formatted as `MM-DD`

#### Scenario: Cross-year day label includes year
- **WHEN** an event date is in a different calendar year from the logic-day anchor
- **THEN** dayLabel is formatted as `YYYY-MM-DD`

#### Scenario: Same-day lines sorted by event name; newer days first
- **WHEN** multiple distinct eventNames occur on multiple calendar days
- **THEN** lines for newer calendar dates appear before older dates
- **AND** within one date, lines are sorted by eventName
