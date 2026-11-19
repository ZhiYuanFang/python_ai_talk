## MODIFIED Requirements

### Requirement: Miss recording MUST use canonical hard failure before soft reply

When the intent path produces a final user-facing failure that matches the existing agent-miss predicate (`infer_miss_fail_kind` or equivalent), the system MUST determine `fail_kind` and write the miss-inbox record using the canonical hard failure text (or equivalent stable failure wording) before any outward miss reply replaces the user-facing `content`. The fixed outward wording MUST NOT be the sole input to miss classification or inbox counting. Confirmation / disambiguation paths MUST remain unrecorded.

#### Scenario: Fixed reply does not skip inbox

- **WHEN** 系统因无法识别事件本将返回硬失败文案且随后对外改为固定话术
- **THEN** 覆盖缺口收件箱 MUST 仍新增一条记录
- **AND** 记录中的失败回复字段 MUST 为规范硬文案（或等价稳定失败文案），不得仅存固定对外话术导致无法归类

#### Scenario: Confirm still skipped

- **WHEN** 系统仅处于确认/消歧中
- **THEN** 系统 MUST NOT 因本能力写入 miss inbox，也 MUST NOT 仅为润色而改写本路径对外文案

### Requirement: Soft reply MUST NOT change miss positioning or barge miss semantics

Outward miss replies（含固定话术）MUST NOT reclassify the turn as a successful non-miss completion for statistics or product positioning. Barge-in concatenate-on-miss decisions MUST continue to treat the turn as agent_miss based on the canonical failure signal (`fail_kind` and/or hard failure text), not solely on whether the outward `content` still contains legacy hard phrases.

#### Scenario: Barge still sees miss

- **WHEN** 占坑轮终局为 miss 且对外已为固定话术，缓冲中仍有插话
- **THEN** 系统 MUST 仍可按既有 miss 拼接重跑规则处理
- **AND** MUST NOT 仅因对外文案缺少「无法识别/估不准」等字样而跳过拼接

## REMOVED Requirements

### Requirement: Adaptive soft reply MAY use optional predict snapshot and baby profile

**Reason**: miss 出口需去掉 AIGC，不再用 LLM + 快照/画像生成软回复。  
**Migration**: 改用固定话术「我只能回答信息记录相关问题」（见 ADDED「Fixed non-AIGC miss reply」）；inbox 仍用硬文案。

## ADDED Requirements

### Requirement: Fixed non-AIGC miss reply

After a miss has been classified and recorded with canonical hard failure text as required above, the system MUST set the outward user `content` to exactly `我只能回答信息记录相关问题`. The system MUST NOT call an LLM to generate or rewrite that miss outward reply. The system MUST NOT recompute predict-algorithm snapshots solely for this reply path.

#### Scenario: Miss outward is fixed phrase

- **WHEN** 意图路径判定为 miss 且已（或即将）用硬文案写入 miss inbox
- **THEN** 返回给用户的 `content` MUST 为「我只能回答信息记录相关问题」
- **AND** MUST NOT 发起 miss 软回复 LLM 调用

#### Scenario: No LLM fallback needed for miss outward

- **WHEN** 本轮为 miss 终局
- **THEN** 对外主路径 MUST 为上述固定话术，MUST NOT 再依赖「LLM 失败回退硬文案」作为对外主路径
