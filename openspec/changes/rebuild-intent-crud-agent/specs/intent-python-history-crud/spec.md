## ADDED Requirements

### Requirement: Python 经 HTTP 执行历史增删改
在意图已确认且不需要继续澄清时，Python 服务 SHALL 通过兄弟仓 history-service **一条**批量 HTTP（`POST /device/history/api/event/batch`）执行喂养记录的增、改、删或结束进行中的记录。系统 MUST NOT 把落库决策留给 Go 语音层根据原文或 `action` 再次判断。既有单条 add/update/delete/end-latest 可保留给 App，意图路径 MUST 走 batch。Python MUST NOT 直连数据库。系统 MUST NOT 因字典外名称创建新事件类型。

#### Scenario: 单次记录走 add
- **WHEN** 意图为 `op=create` 且事件动作为 `one`，叶子 `event_id` 已确定
- **THEN** 系统 SHALL POST add，写入 deviceNo、eventId、数量与时间
- **AND** 成功后 `content` SHALL 为已记录类自然语言（非空）

#### Scenario: 结束进行中走 end-latest
- **WHEN** 意图为 `op=create` 且事件动作为 `end`
- **THEN** 系统 SHALL 调用 end-latest（或先 latest 再 update 结束时间）
- **AND** SHALL NOT 再新增一条仅含结束语义但未关联进行中记录的重复行（除非兄弟仓接口语义如此）

#### Scenario: 删除走 delete
- **WHEN** 意图为 `op=delete` 且已解析到历史行 id
- **THEN** 系统 SHALL POST delete，body 含 id 与 deviceNo
- **AND** 成功后 `content` SHALL 说明已删除

### Requirement: 多事件逐条执行且使用子项字段
当 `events` 长度大于 1 时，系统 SHALL 将全部子项放入同一次 batch 的 `items[]`，每项使用该子项的 `event_id`、`action`、`quantity`。系统 MUST NOT 用整句重新做事件名匹配，MUST NOT 把所有子项数量写死为 1。batch 部分成功时 MUST 做成的做；`content` MUST 同时说明成功项与未成功项及原因（不得假装全部成功）。

#### Scenario: 两件 create 使用各自 event_id
- **WHEN** `events` 为喝奶 `one` 120 与换尿布 `one`
- **THEN** 系统 SHALL 一次 batch 提交两条 create
- **AND** 第一条数量 MUST 为 120，第二条 MUST NOT 被写成 120 除非子项自带该数量

### Requirement: 查记录在意图图内完成
当 `op=read` 或 `target_type=history` 时，系统 SHALL 在意图图内按已定事件（及可选备注）拉取历史并用模板填写 `content`，SHALL NOT 调用 `call_clinic_agent`、`clinic_graph` 或历史答题 LLM。

#### Scenario: 上次某事件时间
- **WHEN** 用户问「上一次拉屎是什么时候」且历史中有该事件
- **THEN** `content` SHALL 基于拉取的历史给出时间点
- **AND** 执行路径 SHALL NOT 进入 clinic 模块图

### Requirement: 未确认不得写库
当 `need_confirm` 为 true 时，系统 MUST NOT 调用 add/update/delete/end-latest，MUST NOT 写入意图缓存。

#### Scenario: 软确认不落库
- **WHEN** 分类或缓存结果需要用户确认
- **THEN** 响应 SHALL 带 `need_confirm` 与 `confirm_message`
- **AND** history-service 写接口在本轮 MUST NOT 被调用

### Requirement: 落库回执必须说明成败
批量执行完成后，`content` SHALL 使用模板说明结果：全部成功时逐项说明已记录/已改/已删；部分成功时同一段同时列出成功项与未成功项及原因；全部失败时只说明原因。系统 MUST NOT 在落库成功后返回空 `content` 或仅依赖 Go 再编话术。系统 MUST NOT 用生成 LLM 编写该回执。

#### Scenario: 部分入库同时说明
- **WHEN** batch 中喝奶 create 成功、换尿布因缺少字典叶子失败
- **THEN** `content` SHALL 同时包含已记录喝奶与换尿布未入库的原因
- **AND** SHALL NOT 只说「好的，已记录」而不提失败项

### Requirement: 禁止创建新事件类型
当用户词不在事件字典中时，系统 MUST NOT 设置 `is_new_event` 并调用设备侧按名称建档。记事件场景 SHALL 将该名称列入 `missing_events` 并在 `content` 或确认话术中说明未操作原因。查记录场景 SHALL 按备注候选处理（见 `history-remark-filter`）。

#### Scenario: 未知名称不建档
- **WHEN** 用户说「记一笔 AD」且字典无 AD
- **THEN** 系统 SHALL NOT 创建名为 AD 的事件类型
- **AND** SHALL 确认或说明 AD 不是单独事件（例如是否记录营养品并写备注 AD）

### Requirement: 分类默认先确认再落库
当意图来自分类 LLM（缓存未命中）时，系统 SHALL 设置 `need_confirm` 且本轮不写库。免确认仅适用于意图缓存高置信命中。多事件 MUST 软确认。父节点 MUST 只消歧、不落库。

#### Scenario: LLM 分类后不直接写库
- **WHEN** 缓存未命中且分类 LLM 返回单次 create 喝奶
- **THEN** 响应 SHALL `need_confirm=true`
- **AND** 本轮 MUST NOT 调用 batch

