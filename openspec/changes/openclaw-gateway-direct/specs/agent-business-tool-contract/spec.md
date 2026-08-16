## MODIFIED Requirements

### Requirement: Intent 写 tool 绑定四单动词 REST
Intent 历史写入 SHALL 通过 Gateway 可调用的四个业务 tools（或等价）绑定 Go：**create/add**、**update**、**delete**、**end-latest**。Intent 主路径 MUST NOT 再依赖 `event/batch`。同轮多写 MUST 先 end 后其余。调用方为 Gateway Intent agent，MUST NOT 为 Go 解析结构化意图后二次批量写。

#### Scenario: create 经 tool
- **WHEN** Intent agent 需要新增一条历史
- **THEN** 系统 MUST 调用 create/add REST tool
- **AND** MUST NOT 要求 Go 再根据意图 JSON 调 batch

### Requirement: Clinic 与 Care 无写 tool
Clinic 与 Care Alert agent 的 tool 策略 MUST NOT 暴露历史写 tools。

#### Scenario: Care 只读业务面
- **WHEN** Care Alert agent 运行
- **THEN** 其 MAY 调用 filter/list 与 profile 等只读 tools
- **AND** MUST NOT 调用 create/update/delete/end
