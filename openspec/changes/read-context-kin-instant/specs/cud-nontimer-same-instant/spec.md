## ADDED Requirements

### Requirement: Non-timer create and update SHALL store one instant

When persisting create or update for an event whose catalog type is not timer, the system MUST set start time and end time to the same Unix second. When both are present and differ, the system MUST use the end time for both. When only the start time is present, the end time MUST copy the start time. Timer events that are still open MUST keep an empty or zero end. Timer events that are a closed duration record MUST keep an end later than the start when the utterance describes a real duration.

#### Scenario: Non-timer with two clocks collapses to end

- **WHEN** 用户补记非计时事件且模型给出的开始与结束不是同一时刻
- **THEN** 落库的开始与结束 MUST 相同
- **AND** MUST 采用结束时间作为该时刻

#### Scenario: Timer duration unchanged

- **WHEN** 用户补记一段计时事件的真实起止
- **THEN** 系统 MUST 保留开始早于结束
- **AND** MUST NOT 把两者收成同一时刻
