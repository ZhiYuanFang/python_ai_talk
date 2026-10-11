## REMOVED Requirements

### Requirement: time 叶形态暧昧时 SHAPE 小 LLM 兜底
**Reason**：形态裁定并入 TYPE 关键字飞轮与 TYPE 小 LLM（`op=end|create` 等），不再维护独立 SHAPE 维与 `rule_gap(shape)`。
**Migration**：结束/开表由 `intent-type-keyword-flywheel` 的 TYPE 路径表达；删除或停用主路径对 SHAPE 小 LLM 的调用。

### Requirement: SHAPE 回写驱动确认与落库
**Reason**：结束语义由 TYPE 结果直接驱动执行/确认，不再经独立 SHAPE 回写步骤。
**Migration**：以 TYPE `op=end`（或等价）驱动 batch 结束路径。

## MODIFIED Requirements

### Requirement: 计时结束口语规则须先于默认开表
当段经 TYPE 飞轮或 TYPE LLM 判定为结束计时（`op=end` 或等价），或类型关键字/提示明确表达「醒了/睡醒/起床」等结束语义时，系统 SHALL 将意图定为结束，MUST NOT 仅因段内含「睡」等喂养词默认 `create`+`start`。独立 SHAPE 小 LLM MUST NOT 再作为必经步骤。

#### Scenario: 睡醒了定为 end
- **WHEN** 用户输入「睡醒了」且 TYPE 路径定为结束睡眠
- **THEN** 拼装结果的 `op` SHALL 为 `end`（或等价结束语义）
- **AND** MUST NOT 询问「现在开始睡眠」
