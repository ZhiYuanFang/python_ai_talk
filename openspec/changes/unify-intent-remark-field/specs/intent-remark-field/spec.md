## ADDED Requirements

### Requirement: 意图备注字段唯一为 remark
系统在意图分析信封、图状态、pending 澄清、分类提示词与意图缓存载荷中，SHALL 仅使用字段名 `remark`（含子项 `events[].remark`）表示备注专名或明细。系统 MUST NOT 定义、读写、序列化或在提示词 JSON 模板中使用字段名 `remark_keyword`。

#### Scenario: 分类输出使用 remark
- **WHEN** 用户说「吃菠菜了」且分类判定为 create「辅食」并带明细专名
- **THEN** 意图结果 SHALL 在对应 `events[]` 项上以 `remark` 承载该专名（如「菠菜」）
- **AND** MUST NOT 使用 `remark_keyword` 承载该专名

#### Scenario: 运行时与提示词无 remark_keyword
- **WHEN** 本变更实现完成
- **THEN** 分类 system 提示词与运行时意图路径（分类/确认/落库/查史/匹配）MUST NOT 再使用字段名 `remark_keyword`
- **AND** 旧 JSON 键名 MAY 仅出现在受 env 控制的 Chroma 一次性迁移实现中（用于读取并删除旧键）

### Requirement: 启动可选迁移 Chroma 旧备注键
系统 SHALL 提供环境变量（默认关闭），为 true 时在应用启动且意图缓存已初始化后，扫描 Chroma 集合 `feeding_intents` 各条目的 metadata payload：将顶层与 `events[]` 中的旧键 `remark_keyword` 在对应 `remark` 为空时写入 `remark`，并 MUST 删除旧键。本迁移 MUST NOT 修改 MySQL 或兄弟仓历史表。当「启动清空 feeding_intents」开关同时为 true 时，系统 MUST 跳过本迁移（清空优先）。迁移完成后日志 SHALL 提示运维将开关改回 false。

#### Scenario: 空 remark 时从旧键回填
- **WHEN** 某条 payload 顶层或子项仅有旧键值为「菠菜」且 `remark` 为空，且迁移开关为 true、清空开关为 false
- **THEN** 系统 SHALL 将该处 `remark` 设为「菠菜」并删除旧键

#### Scenario: 已有 remark 不覆盖
- **WHEN** 同条已有非空 `remark` 且仍带旧键
- **THEN** 系统 MUST NOT 用旧键覆盖 `remark`
- **AND** SHALL 删除旧键

#### Scenario: 清空优先
- **WHEN** 启动清空开关与迁移开关均为 true
- **THEN** 系统 SHALL 执行清空（或等价）且 MUST NOT 再对已清空集合做旧键迁移

#### Scenario: 默认不迁
- **WHEN** 迁移开关为 false 或未配置
- **THEN** 系统 MUST NOT 因启动而改写 feeding_intents 的备注字段

### Requirement: create 落库写入 history.remark
当子项 `op` 为 create（及同样走 batch 且携带备注的 update 等 CUD）且 `events[].remark`（或约定顶层 `remark`）去空白后非空时，系统在调用兄弟仓 batch 时 MUST 将该字符串写入请求项的 `remark` 字段，使落库后的喂养历史记录备注非空。

#### Scenario: 吃菠菜了确认后记录带备注
- **WHEN** 意图为 create「辅食」且 `events[].remark` 为「菠菜」，用户确认后 batch 至少一条成功
- **THEN** 提交给 history-service 的对应 item 的 `remark` SHALL 为「菠菜」

#### Scenario: 无备注时 remark 可空
- **WHEN** create 子项未带非空 `remark`
- **THEN** batch item 的 `remark` SHALL 为空串或等价省略，MUST NOT 臆造专名

### Requirement: read 与备注反查使用 remark
查记录拉史与分类后备注反查路径 SHALL 从意图子项或顶层的 `remark` 读取专名，并作为 filter 查询参数 `remark` 传递。系统 MUST NOT 再从 `remark_keyword` 读取筛选专名。

#### Scenario: 按备注筛选拉史
- **WHEN** read 子项带非空 `remark`（如「AD」）且执行查史
- **THEN** 系统调用 filter 时 SHALL 传递该 `remark` 值

#### Scenario: 反查命中写回 remark
- **WHEN** 备注反查唯一命中字典叶子
- **THEN** 系统 SHALL 将专名写回意图的 `remark`（子项与/或顶层），MUST NOT 写入 `remark_keyword`
