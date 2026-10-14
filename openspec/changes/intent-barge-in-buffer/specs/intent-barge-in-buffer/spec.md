## ADDED Requirements

### Requirement: One intent graph per device at a time

When a feeding intent analyze request arrives for a `device_no`, if that device already has an in-flight intent run (busy), the system MUST NOT start a second intent graph for that request. The new utterance MUST be appended to the device barge-in buffer. If the device is not busy, the system MUST mark busy and run the intent graph on that request’s text as the anchor utterance.

#### Scenario: Second POST while busy buffers only

- **WHEN** device D 已有意图图在跑，再次 POST 意图分析且 text 为 B
- **THEN** 系统 MUST 将 B 写入 D 的插话缓冲
- **AND** MUST NOT 为该请求再启动一张意图图

#### Scenario: Idle POST starts run

- **WHEN** device D 无进行中意图图
- **THEN** 系统 MUST 以本次 text 为锚点启动意图图并置 busy

### Requirement: Busy follow-up requests SHALL await round completion

A request that finds the device busy MUST wait (hang) until the in-flight round finishes, including any agent_miss-driven concatenate re-runs started for that round, before returning. The hanging request MUST NOT stream a separate thinking bubble sequence. The owner (busy-holding) connection SHALL carry the full SSE thinking and final answer for the round. After completion, hanging requests MAY receive the same final answer snapshot or a lightweight merged-handled response.

#### Scenario: Hanging waiter gets no second thinking track

- **WHEN** busy 期间第二次 stream 请求挂起
- **THEN** 该挂起连接 MUST NOT 独立推送一套完整 thinking 流程
- **AND** 占坑连接 MUST 仍可推送本轮（含重跑）的 thinking 与终答

### Requirement: Agent-miss SHALL concatenate buffer and re-run up to five times

When the in-flight run finishes with a final failure that matches the existing agent_miss predicate (`infer_miss_fail_kind` / equivalent: event unresolved, other unsupported, predict uncertain with 估不准/暂时无法, segment unclear phrases), and the buffer is non-empty, the system MUST concatenate the anchor utterance with all buffered utterances in order into one text, MUST clear the buffer immediately after forming that text, and MUST re-run intent analysis on the concatenated text. Re-runs for the same busy occupancy MUST NOT exceed 5. The phrases「数据量太少，无法预测」MUST NOT by itself be treated as agent_miss for this concatenate trigger.

#### Scenario: Miss with buffer concatenates once

- **WHEN** 本轮终答命中 agent_miss 且缓冲含后续语句
- **THEN** 系统 MUST 全量拼接锚点与缓冲后清缓冲并重跑
- **AND** 重跑计数 SHALL 受最多 5 轮限制

#### Scenario: Data-too-few does not concatenate

- **WHEN** 终答为「数据量太少，无法预测」类且未命中 agent_miss 其它规则
- **THEN** 系统 MUST NOT 仅因此拼接缓冲重跑
- **AND** MUST 丢弃缓冲并结束本轮（释放 busy）

### Requirement: Successful or confirm outcomes discard buffer

When the run ends with a successful user-facing answer, or enters confirmation / disambiguation (`need_confirm`, options, or confirm_type), the system MUST discard the device barge-in buffer and MUST NOT concatenate for re-run solely due to buffered mid-thinking utterances.

#### Scenario: Confirm discards barge buffer

- **WHEN** 本轮进入需确认或消歧
- **THEN** 系统 MUST 清空该 device 插话缓冲
- **AND** MUST NOT 将缓冲拼进确认前的原文重跑

### Requirement: Buffer MUST clear on end, re-run start, error, and TTL

The device barge-in buffer MUST be cleared when the intent run completes normally (success, confirm, miss finalize after concat scheduling, or terminal miss without re-run), when a concatenate re-run starts, and when the run fails with an unhandled exception. Buffered state MUST also expire automatically after 10 minutes TTL to prevent stuck state.

#### Scenario: Exception clears buffer

- **WHEN** 意图处理过程抛出未恢复异常
- **THEN** 系统 MUST 清空该 device 缓冲并释放 busy

#### Scenario: Ten-minute TTL

- **WHEN** 缓冲或 busy 状态超过 10 分钟未按业务路径清除
- **THEN** 系统 MUST 允许该状态因 TTL 失效，使后续请求可重新占坑
