## ADDED Requirements

### Requirement: 用 conversation_id 与 pending 判断首轮
意图路径 SHALL 用请求中的 `conversation_id` 加上内存澄清仓（`clarification_store`）是否存在 pending 来判断是否连续对话。系统 MUST NOT 把 clinic 陪伴会话当作意图 CRUD 的上下文。系统本变更 MUST NOT 依赖每轮对话全文账本才能工作。

#### Scenario: 无 conversation_id 视为首轮
- **WHEN** 请求未带 `conversation_id`（或空）且澄清仓无对应 pending
- **THEN** 系统 SHALL 按新对话处理（可走意图缓存或分类）
- **AND** SHALL NOT 读取 clinic companion_session 作为本轮意图上下文

#### Scenario: 有 cid 无 pending 视为新一轮意图
- **WHEN** 请求带已有 `conversation_id` 但澄清仓无该 id 的 pending
- **THEN** 系统 SHALL 按独立意图处理（可命中意图缓存）
- **AND** SHALL NOT 把上一轮已结束的确认状态当作仍有效

#### Scenario: 有 cid 且有 pending 视为连续确认
- **WHEN** 请求带 `conversation_id` 且澄清仓存在 pending
- **THEN** 系统 SHALL 先硬匹配「是的 / 1 / 取消」类回复
- **AND** 硬匹配未中且为自由文本时 MAY 调用澄清 LLM
- **AND** 硬匹配命中时 MUST NOT 调用澄清 LLM
