## ADDED Requirements

### Requirement: 计时结束口语规则须先于默认开表
当段文本匹配结束态口语线索（含「结束」「停了」「醒了」「睡醒」「起床」等实现所定词表）且事件为计时叶或尚未定事件但 TYPE 已判定 feeding 时，系统 SHALL 将 `op` 定为 `end`（或等价结束），MUST NOT 仅因段内含「睡」等喂养线索而默认 `create`+`start`。

#### Scenario: 睡醒了规则标 end
- **WHEN** 用户输入「睡醒了」且事件维已定为「睡眠」（或等价 type=time 叶）
- **THEN** 拼装结果的 `op` SHALL 为 `end`（或 action 为 end 的结束语义）
- **AND** 确认话术 SHALL 表达结束睡眠，MUST NOT 询问「现在开始睡眠」

### Requirement: time 叶形态暧昧时 SHAPE 小 LLM 兜底
当事件已定为 `type=time` 叶子，规则未给出明确结束/开表裁定（或开/关线索冲突）时，系统 SHALL 调用 SHAPE 小 LLM（提示词在 `prompts/system.py`），输出仅限 `op`/`action` 组合：`create+start`、`end+end`、`create+one`。MUST NOT 修改 `event_id`/`event_name`。调用 MUST 经 SSE 真流式透出中文 reasoning，并写入 `rule_gap` 且 `llm_used=true`。LLM 失败时 SHALL 回退规则推导，MUST NOT 回退满血 classify。

#### Scenario: 暧昧计时态走 SHAPE LLM
- **WHEN** 计时叶已定且规则无法唯一判定开始或结束
- **THEN** 系统 SHALL 调用 SHAPE 小 LLM 得到允许的 op/action 组合
- **AND** 缺口记录 SHALL 含 `dimension=shape` 与 `llm_used=true`

#### Scenario: 睡着了保持开始
- **WHEN** 用户输入「睡着了」且事件定为睡眠类 time 叶，无结束态「醒」类线索
- **THEN** 结果 SHALL 为开始计时语义（create+start 或等价）
- **AND** MUST NOT 误判为结束睡眠

### Requirement: SHAPE 回写驱动确认与落库
当 SHAPE 规则或小 LLM 将形态定为结束时，系统 MUST 将意图项的 `op`/`action` 写为结束语义，使确认话术与后续 batch 走结束路径（如「现在结束「睡眠」」），与 create+start 开表路径区分。

#### Scenario: 结束确认文案
- **WHEN** 「睡醒了」经 SHAPE 定为结束睡眠
- **THEN** 用户可见确认问句 SHALL 含结束语义
- **AND** SHALL NOT 含「现在开始」对该睡眠项的开表表述
