## ADDED Requirements

### Requirement: Intent 对 Go 仅自然语言 reply
Intent Gateway agent 对 Go 的产品返回 SHALL 为自然语言 reply（及可选 thinking/流式事件）。系统 MUST NOT 再要求 Go 解析 `target_type`、`events[]`、`need_confirm`、`missing_events` 等结构化意图信封以决定落库。

#### Scenario: 成功写奶记录
- **WHEN** 用户说「喂了 120 毫升奶」且 Intent agent 调用 create（或等价）tool 成功
- **THEN** Go MUST 仅需向用户播报 agent 的自然语言 reply
- **AND** Go MUST NOT 再根据 JSON events 二次调用 history 写接口完成同一意图

#### Scenario: 删除结构化契约
- **WHEN** 检索 Go 意图客户端与 Python 意图 HTTP 响应模型
- **THEN** 作为产品权威的结构化意图响应契约 MUST 被删除或标记废弃且无调用方
- **AND** 新代码 MUST NOT 再新增对该信封的依赖

### Requirement: 落库仅经 Gateway tools
Intent 历史写入 SHALL 仅通过 Gateway 调用的业务 tools 完成（对齐 Go 四单动词 REST：add/update/delete/end-latest；读为 filter/list 等）。同一用户回合内若需结束计时再写入，agent/tools MUST 先 end 后其余写操作。

#### Scenario: 多事件先 end
- **WHEN** 同一回合需要 end 某计时事件并 create 另一事件
- **THEN** tool 调用顺序 MUST 先 end（或等价）再执行其余写操作
