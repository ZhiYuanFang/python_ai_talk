## ADDED Requirements

### Requirement: TYPE 冷路径仅 LLM 声明时确认
当类型结果来自 TYPE 小 LLM 时，系统 SHALL 仅在模型输出 `need_confirm=true` 时向用户确认类型意图；当 `need_confirm=false` 时 MUST NOT 仅因类型来自 LLM 而强制 `leaf_confirm`。父事件消歧与 number 缺量追问等阻塞澄清不受本条取消。

#### Scenario: 高置信类型不二次确认
- **WHEN** TYPE LLM 对「睡了多久了」返回 history+read 且 `need_confirm=false`，且无其它阻塞
- **THEN** 系统 SHALL 继续查史执行路径
- **AND** MUST NOT 先问「您是要查询睡眠吗」类类型确认

#### Scenario: 模型要求确认则询问
- **WHEN** TYPE LLM 返回 `need_confirm=true`
- **THEN** 系统 SHALL 向用户确认后再采纳该类型结果（及写入 keywords）
