## MODIFIED Requirements

### Requirement: Parent hit forces disambiguation
名称、向量或 LLM 任一路径在 **create/update/delete（喂养落库）** 命中父事件时，系统 MUST 强制消歧：返回该父类下的子事件选项与澄清问句，并写入 pending 会话状态。MUST NOT 以父事件高置信直接结束 feeding 落库。本条 MUST NOT 适用于 `op=read` / `target_type=history`：查记录命中父事件走是/否确认后展开叶子拉史，不得改成选叶子。

#### Scenario: Parent name triggers child options
- **WHEN** 用户输入精确匹配某父事件的 `event_name`（或约定的等价名称字段）
- **AND** 该句不是查记录句式
- **AND** 该父事件存在一个或多个子事件
- **THEN** 响应 SHALL 进入消歧状态
- **AND** SHALL 包含子事件选项列表与澄清问句
- **AND** SHALL 提供可用于续聊的 `conversation_id`

#### Scenario: Vector or LLM parent hit is rewritten to disambiguation
- **WHEN** 分类得到的 `event_id` 为父事件
- **AND** `op` 为 create、update 或 delete
- **THEN** 系统 MUST NOT 以该父事件高置信直接结束 feeding
- **AND** MUST 改写为针对其子事件的消歧响应

#### Scenario: History parent hit is not child picker
- **WHEN** 分类 `op=read` 且 `event_id` 为父事件
- **THEN** 系统 MUST NOT 进入 `parent_disambiguation` 选叶子
- **AND** SHALL 按查记录确认或缓存命中路径处理该父 id

## ADDED Requirements

### Requirement: 确认查父后按 op 展开不得改消歧
当 pending 为查记录确认（`op=read`）且待确认事件为父事件，用户肯定后系统 MUST 清 pending，MUST 递归展开该父下全部叶子并拉史播报，MUST NOT 创建 `parent_disambiguation` pending。当 pending 为 create/update/delete 且目标为父，系统 MUST 仍进入父事件消歧。

#### Scenario: Confirm query diaper expands leaves
- **WHEN** pending 为查询父事件「换尿布」且用户回复确认
- **THEN** 系统 SHALL 查询其子孙叶子（如尿尿、拉屎）的历史
- **AND** SHALL NOT 再问用户选择尿尿或拉屎

#### Scenario: Confirm create parent still disambiguates
- **WHEN** pending 为记录父事件「换尿布」且用户回复确认或纠正到该父
- **THEN** 系统 SHALL 进入子事件消歧
- **AND** SHALL NOT 以父事件落库
