## ADDED Requirements

### Requirement: 单事件向量不得吞掉多事件或非 create
事件名向量匹配若作为冷启动辅助，仅当用户句为单一 create（`start|end|one` 之一）且非查询句式、非复合多事件时，才允许以高置信直接作为执行意图。系统 MUST NOT 因 Top-1 事件名相似而将明显多事件句或查/改/删句直接定为单条 feeding create。意图缓存命中时 MUST 优先于本条事件名匹配。

#### Scenario: 复合句不因高分只记一件
- **WHEN** 用户输入「吃完奶，换了尿布」
- **AND** 向量 Top-1 为喝奶且分数高于高置信阈值
- **THEN** 系统 SHALL NOT 以该单事件直接 END 并跳过 LLM/多事件分类
- **AND** SHALL 进入分类或意图缓存路径以保留多事件可能

#### Scenario: 查询句仍不得向量落 feeding
- **WHEN** 用户输入「上一次拉屎是什么时候」
- **THEN** 事件名向量阶段 SHALL NOT 以 feeding create 高置信直接结束

## MODIFIED Requirements

### Requirement: 系统使用向量相似度进行喂养事件匹配
系统 MAY 使用向量数据库对用户输入与标准事件名（及动作变体）做语义匹配，作为单次 create 的冷启动辅助。系统 MUST NOT 依赖 `source=user` 历史用户表达作为主匹配源。高置信直接执行仅适用于单一 create 且未命中意图缓存、非复合句、非查询句。

#### Scenario: 向量匹配成功（单一 create）
- **WHEN** 用户输入「开始睡眠」
- **AND** 标准事件向量中存在对应开始变体
- **AND** 句式非查询、非多事件
- **AND** 意图缓存未命中
- **THEN** 系统可直接判定为 create/start 并进入执行或确认
- **AND** SHALL NOT 再写入单事件用户表达飞轮

#### Scenario: 向量匹配中等置信度（单一 create）
- **WHEN** 用户输入「母乳」且为单一 create、非查询、非多事件
- **AND** 标准事件名中等置信
- **THEN** 系统需要用户确认后才执行 create
- **AND** 本轮 MUST NOT 写库

#### Scenario: 向量匹配低置信度降级 LLM
- **WHEN** 用户输入未达高/中置信
- **THEN** 系统走 LLM 分类流程进行意图识别（含 CRUD 与 multi）
