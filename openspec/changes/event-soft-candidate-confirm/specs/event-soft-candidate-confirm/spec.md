## ADDED Requirements

### Requirement: EVENT 软候选须确认后方可执行
当段 EVENT 维经词典名、`extra_names`、短说法向量高置信命中与 Go 备注反查仍未得到唯一 `event_id`，且 EVENT 小 LLM 返回一个或多个表内候选时，系统 SHALL 进入确认或消歧 pending，MUST NOT 在用户确认/点选之前执行落库、查史播报或预测播报，MUST NOT 写入事件短说法飞轮。候选 `event_id`/`event_name` MUST 来自注入的字典叶子表；MUST NOT 编造表外 id 或新建事件类型。

#### Scenario: 午饭预测问单候选软确认
- **WHEN** 用户说「接下来几点钟吃午饭」，TYPE 已判定为 read 且 `read_source=predict`，EVENT 梯子未硬命中，EVENT 小 LLM 唯一候选为表内「辅食」
- **THEN** 系统 SHALL 返回叶子软确认，话术 SHALL 询问用户是否在问接下来几点钟吃辅食（或语义等价，须点出「辅食」）
- **AND** MUST NOT 仅返回「无法识别对应的事件「午饭」」
- **AND** MUST NOT 在确认前调用预测播报成功路径

#### Scenario: 多候选消歧
- **WHEN** EVENT 小 LLM 返回两个及以上表内候选（不超过实现上限）
- **THEN** 系统 SHALL 挂带 options 的消歧 pending，选项为这些候选叶子
- **AND** MUST NOT 静默采用 Top1 执行

#### Scenario: 无候选仍无法识别
- **WHEN** EVENT 小 LLM 返回空候选列表（或无法解析出任何表内合法 id）
- **THEN** 系统 SHALL 反馈无法识别对应事件（或引导重说）
- **AND** MUST NOT 回退满血 classify

### Requirement: 确认或点选后写短说法飞轮
当用户对 EVENT 软候选确认（单候选）或从多候选中点选某一叶子后，系统 SHALL 将段核词（优先备注/口语核词抽取结果，如「午饭」）作为 document 写入事件短说法飞轮，指向所选 `event_id`。用户拒绝或取消时 MUST NOT 写入该飞轮。飞轮 document MUST NOT 使用带完整问法/时间的整句作为默认写入内容。

#### Scenario: 确认辅食后午饭可飞轮
- **WHEN** 用户确认「午饭」对应「辅食」
- **THEN** 系统 SHALL 写入短说法（核词含「午饭」或等价）→ 辅食 `event_id`
- **AND** 随后同设备再出现以「午饭」为核心的对齐时，SHALL 可被短说法向量路径硬命中（在阈值满足时），无需再次仅因同一映射走软确认

#### Scenario: 拒绝不写飞轮
- **WHEN** 用户拒绝当前软候选或取消消歧
- **THEN** 系统 MUST NOT 将该口语写入指向猜测叶的短说法飞轮
