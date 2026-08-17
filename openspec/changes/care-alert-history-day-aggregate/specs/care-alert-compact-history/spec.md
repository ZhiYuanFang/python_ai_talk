## MODIFIED Requirements

### Requirement: Care-alert history uses compact two-day lines
Care-alert analyze prompts SHALL inject feeding/care history as compact lines covering only Shanghai calendar today and yesterday, not full JSON. History SHALL be aggregated by calendar day and `eventName` into lines of the form `{dayLabel}·{eventName}·{clockList}·{totalSegment}` where:

- `dayLabel` is `今天` or `昨天`
- `clockList` is each occurrence's start time as `HH:MM`, ordered ascending by startTime within the group, joined by `/`
- `totalSegment` depends on event type (`number` | `time` | `one`):
  - **time**: sum of valid durations, total seconds converted to minutes with round-half-up, rendered as `总时长XhYm` (omit `0h` when hours are zero; if no valid duration, `总时长0m`)
  - **number**: `总量{sumOfEventNumber}{unit}` where unit is taken from the first non-empty `eventUnit` / `event_unit` / `unit` in the group (omit unit suffix when empty)
  - **one**: `{occurrenceCount}次`

Within the same day, lines SHALL be ordered by `eventName`. The prompt SHALL emit today's groups before yesterday's. Relative Chinese phrases such as `刚刚` / `N分钟前` MUST NOT be used in these aggregated lines. History lines MUST NOT include eventId.

#### Scenario: Aggregated line for timer events
- **WHEN** care-alert builds the user message and the same eventName occurs multiple times today as timer events with valid start/end
- **THEN** one line is emitted for that day and name with ascending `HH:MM` clocks and a `总时长XhYm` total
- **AND** the history line does not contain an eventId

#### Scenario: Aggregated line for count events with unit
- **WHEN** care-alert builds history for count events sharing a name on yesterday with eventNumber values and an eventUnit
- **THEN** the line uses `总量` equal to the sum of eventNumber followed by that unit
- **AND** clocks are listed as `HH:MM` joined by `/`

#### Scenario: One-shot events use occurrence count
- **WHEN** care-alert aggregates one-shot events for a name on today
- **THEN** the total segment is `{N}次` where N is the number of occurrences that day

#### Scenario: Older days excluded from prompt
- **WHEN** history_events include records from before yesterday (Shanghai)
- **THEN** those records are not included in the compact history block

#### Scenario: Same-day lines sorted by event name
- **WHEN** multiple distinct eventNames occur on today
- **THEN** today's aggregated lines appear sorted by eventName before any yesterday lines
