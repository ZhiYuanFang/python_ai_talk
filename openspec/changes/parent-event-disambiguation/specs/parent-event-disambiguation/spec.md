## ADDED Requirements

### Requirement: Parent events must not be recorded

系统 MUST NOT 将带有子事件的父事件作为最终喂养落库 `event_id`。仅无子节点的叶子事件允许进入 feeding 落库与数据飞轮写入。落库结果 MUST 精确到子事件。

#### Scenario: Leaf event can be finalized

- **WHEN** 匹配结果的 `event_id` 在当前事件字典中不作为任何事件的 `parent_id`
- **THEN** 系统 MAY 将该事件作为喂养意图最终结果返回或落库

#### Scenario: Parent event cannot be finalized

- **WHEN** 匹配结果的 `event_id` 出现在任一事件的非空 `parent_id` 集合中
- **THEN** 系统 MUST NOT 直接作为 feeding 最终结果落库
- **AND** MUST 进入父事件消歧流程

### Requirement: Parent hit forces disambiguation

名称、向量或 LLM 任一路径命中父事件时，系统 MUST 强制消歧：返回该父类下的子事件选项与澄清问句，并写入 pending 会话状态。MUST NOT 以父事件高置信直接结束 feeding。

#### Scenario: Parent name triggers child options

- **WHEN** 用户输入精确匹配某父事件的 `event_name`（或约定的等价名称字段）
- **AND** 该父事件存在一个或多个子事件
- **THEN** 响应 SHALL 进入消歧状态
- **AND** SHALL 包含子事件选项列表与澄清问句
- **AND** SHALL 提供可用于续聊的 `conversation_id`

#### Scenario: Vector or LLM parent hit is rewritten to disambiguation

- **WHEN** 向量匹配或 LLM 分类得到的 `event_id` 为父事件
- **THEN** 系统 MUST NOT 以该父事件高置信直接结束 feeding
- **AND** MUST 改写为针对其子事件的消歧响应

### Requirement: Free-text continuation on same intent endpoint

主交互 MUST 使用同一意图输入接口与同一输入框。请求 MAY 携带 `conversation_id`。用户对澄清问句的回应 MUST 视为自由文本（任意内容都可能出现），MUST NOT 要求 `confirm|reject` 枚举才能继续。

#### Scenario: Continue disambiguation with typed reply

- **WHEN** 上一轮已返回消歧 pending 与 `conversation_id`
- **AND** 用户在同一意图输入框提交任意自由文本并带回该 `conversation_id`
- **THEN** 系统 SHALL 在 pending 选项语境下解析该文本

#### Scenario: Unique child resolved from free text

- **WHEN** pending 消歧存在
- **AND** 用户文本唯一匹配某一子选项（名称、`extra_names` 或序号）
- **THEN** 系统 SHALL 清 pending
- **AND** SHALL 以该叶子事件作为喂养意图结果
- **AND** MAY 在此后触发数据飞轮写入

#### Scenario: Ambiguous reply asks again

- **WHEN** pending 消歧存在
- **AND** 用户文本匹配到多个子选项
- **THEN** 系统 SHALL 保持 pending
- **AND** SHALL 再次返回澄清问句与选项（可缩小）

#### Scenario: Explicit reject clears pending

- **WHEN** pending 消歧存在
- **AND** 用户文本为明确拒绝词（如取消、不是、算了）
- **THEN** 系统 SHALL 清 pending
- **AND** SHALL NOT 落库父事件或任意子事件

#### Scenario: Any other reply treated as new intent

- **WHEN** pending 消歧存在
- **AND** 用户文本既非唯一选项命中、亦非明确拒绝、亦非多选项模糊命中
- **THEN** 系统 SHALL 清 pending
- **AND** SHALL 将本句作为新意图重新执行完整意图流程
- **AND** SHALL NOT 因「非法回复」而卡死在消歧状态

### Requirement: Flywheel only after unique leaf resolution

数据飞轮 MUST 仅在消歧成功并落到唯一叶子事件之后写入；父事件 MUST NOT 写入飞轮。消歧中途的短回复（如序号）MUST NOT 单独作为用户表达入库。

#### Scenario: Flywheel writes after leaf chosen

- **WHEN** 消歧成功得到唯一叶子 `event_id`
- **AND** 消歧前触发父命中的用户原话适合作为该叶子的表达样本
- **THEN** 系统 MAY 调用飞轮将该表达关联到该叶子事件

#### Scenario: Parent never enters flywheel

- **WHEN** 匹配或分类结果为父事件
- **THEN** 系统 MUST NOT 将父事件作为飞轮写入目标
