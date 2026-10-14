## ADDED Requirements

### Requirement: Miss recording MUST use canonical hard failure before soft reply

When the intent path produces a final user-facing failure that matches the existing agent-miss predicate (`infer_miss_fail_kind` or equivalent), the system MUST determine `fail_kind` and write the miss-inbox record using the canonical hard failure text (or equivalent stable failure wording) before any adaptive soft reply replaces the outward `content`. Soft reply wording MUST NOT be the sole input to miss classification or inbox counting. Confirmation / disambiguation paths MUST remain unrecorded.

#### Scenario: Soft reply does not skip inbox

- **WHEN** 系统因无法识别事件本将返回硬失败文案且随后生成软回复给用户
- **THEN** 覆盖缺口收件箱 MUST 仍新增一条记录
- **AND** 记录中的失败回复字段 MUST 为规范硬文案（或等价稳定失败文案），不得仅存软回复导致无法归类

#### Scenario: Confirm still skipped

- **WHEN** 系统仅处于确认/消歧中
- **THEN** 系统 MUST NOT 因本能力写入 miss inbox，也 MUST NOT 仅为润色而调用本 miss 软回复路径

### Requirement: Adaptive soft reply MAY use optional predict snapshot and baby profile

After a miss has been classified and recorded as required above, the system SHALL generate the outward user `content` via an LLM that receives at least the user utterance and the canonical failure semantics. The prompt MUST include the device predict-algorithm Redis snapshot when present and not expired, and MUST omit that block when missing or expired without recomputing the algorithm solely for this reply. The prompt MUST include baby basic profile fields when available, and MUST omit them when unavailable. The LLM MUST use Chinese reasoning; on intent SSE paths the call MUST use `stream(thinking_enabled=True)`. On LLM failure the system MUST fall back to the canonical hard failure text.

#### Scenario: Snapshot present

- **WHEN** 设备存在未过期的预测算法快照且本轮为 miss 软回复
- **THEN** 软回复 LLM 提示 MUST 包含该快照（或其中可读摘要）
- **AND** MUST NOT 为本次软回复重新拉取近 7 日并重算间隔

#### Scenario: Snapshot absent

- **WHEN** 预测算法快照缺失或已过期且本轮为 miss 软回复
- **THEN** 提示 MUST NOT 假装存在预测快照
- **AND** 系统仍 SHALL 可仅凭原话、规范失败语义与（若有）宝宝信息生成软回复或回退硬文案

### Requirement: Soft reply MUST NOT change miss positioning or barge miss semantics

Adaptive soft replies MUST NOT reclassify the turn as a successful non-miss completion for statistics or product positioning. Barge-in concatenate-on-miss decisions MUST continue to treat the turn as agent_miss based on the canonical failure signal (`fail_kind` and/or hard failure text), not solely on whether the soft reply still contains legacy hard phrases.

#### Scenario: Barge still sees miss

- **WHEN** 占坑轮终局为 miss 且已软回复，缓冲中仍有插话
- **THEN** 系统 MUST 仍可按既有 miss 拼接重跑规则处理
- **AND** MUST NOT 仅因软文案缺少「无法识别/估不准」等字样而跳过拼接
