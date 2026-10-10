## ADDED Requirements

### Requirement: 事件短说法为唯一意图向量飞轮单位
系统 SHALL 使用 Chroma 集合（可仍名 `feeding_intents`）存储 **短说法 → 事件** 映射：`document` 为单事件说法或别名，metadata 至少含 `event_id`、`event_name`、`kind`（parent|leaf）。系统 MUST NOT 再将「整句 → 整包多 events 意图 payload」作为可免确认回放的飞轮单位。

#### Scenario: 命中短说法只定事件
- **WHEN** 段文本与库内「尿尿了」短说法相似度 ≥ 0.72
- **THEN** 事件维 SHALL 采用对应 `event_id`
- **AND** SHALL NOT 因命中而直接免确认执行一份历史整包 multi-events 载荷

### Requirement: 相似度门槛 0.72
事件维向量检索采纳 MUST 要求相似度分数 ≥ **0.72**；低于该值 SHALL 视为未命中并进入词典已尝试后的事件小 LLM 兜底或失败重说路径。

#### Scenario: 分数不足
- **WHEN** Top-1 短说法 score &lt; 0.72
- **THEN** 系统 SHALL NOT 采用该条 event_id 作为高置信事件维结果

### Requirement: 确认后只写短说法
用户确认（或等价成功落库）后，系统 MAY 将 **段级** 原文或规范化短句写入事件说法库并关联所确认叶子/父事件。MUST NOT 写入未拆分的复合整句作为 document。

#### Scenario: 复合句确认后分条写入
- **WHEN** 用户确认包含多段 create 的拼装结果且落库成功
- **THEN** 系统 MAY 为各段分别写入短说法
- **AND** MUST NOT 将整句复合原文作为单条 document 绑定单一叶子

### Requirement: 发版清空重建不迁旧整包
上线本能力时系统 SHALL 支持一次性清空该集合（如既有 `CLEAR_FEEDING_INTENTS_ON_STARTUP` / `reset_collection`），并 SHALL 以事件字典名与别名种子重建短说法。MUST NOT 将旧整包意图 payload 自动迁移为新条。

#### Scenario: 清空后无旧串台条
- **WHEN** 运维执行清空并完成种子灌入
- **THEN** 库中 SHALL NOT 残留「换尿布，发现拉臭臭了」→ 整包 create 拉屎 类旧载荷可被整句复合输入免确认回放

### Requirement: 命中须打对照日志
事件维向量命中时，系统 SHALL 记录段原文（或查询文本）、库内 `document`、score、event_id（及可选 vector id），便于排查与灌种。

#### Scenario: 日志含库原文
- **WHEN** 事件维向量命中成功
- **THEN** 日志 SHALL 同时包含查询侧文本与匹配到的数据库 document 原文
