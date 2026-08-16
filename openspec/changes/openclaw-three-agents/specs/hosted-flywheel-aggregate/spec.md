## ADDED Requirements

### Requirement: 仅我方托管聚合飞轮
系统 SHALL 仅提供我方托管的聚合数据飞轮作为 Agent 学习护城河。业务 history API 可 BYO；飞轮存储与聚合基址 MUST 锁定为我方服务，MUST NOT 被客户配置覆盖为自有飞轮后端。理念：使用 Agent 的租户越多，聚合飞轮越强。

#### Scenario: 业务 API 可配、飞轮不可配走
- **WHEN** 接入方配置自定义 history.create 等业务 tool URL
- **THEN** 飞轮 retrieve/record 请求 MUST 仍指向我方 flywheel 基址
- **AND** MUST NOT 提供将飞轮基址改为客户域名的正式配置项

### Requirement: 三 Agent 飞轮物理隔离
Intent、Clinic、Care Alert 的飞轮数据 MUST 分仓（独立 collection/key 前缀/账本），MUST NOT 互相写入对方仓。删除 tip 后，Clinic 飞轮 MUST NOT 再依赖 tip 合成对话轮作为输入。

#### Scenario: Intent 成功不写 qa 仓
- **WHEN** Intent 确认并落库成功触发飞轮写入
- **THEN** 系统 MUST 写入 Intent 飞轮仓
- **AND** MUST NOT 因此写入 Clinic qa_fast_path 或 Care Alert ledger

### Requirement: Intent 飞轮可移植结构
跨租户聚合时，Intent 飞轮缓存 MUST 以可移植结构存储（规范化说法 + 事件名/动作等），MUST NOT 将某一租户的 `event_id` 作为全局可复用落库主键。执行写 tool 前 MUST 通过该租户事件字典将名称解析为对方 id。

#### Scenario: 缓存命中后按对方字典解析
- **WHEN** 飞轮命中一条含事件名的可移植意图结构
- **AND** 当前租户事件字典可解析该名称
- **THEN** 系统 MUST 解析为该租户 event id 再调用写 tool
- **AND** MUST NOT 直接使用缓存中的外租户 event_id（若有）落库

### Requirement: 飞轮经稳定读写面
Agent 运行时 SHALL 仅通过稳定的飞轮读写面（如 retrieve / record_outcome）访问飞轮。确认落库成功、Clinic 隐式采纳、Care Alert ignore|follow_up 等闭环 MUST 调用 record_outcome（或等价）。

#### Scenario: 确认成功上报 outcome
- **WHEN** Intent 用户确认且至少一条写 tool 成功
- **THEN** 系统 MUST 调用飞轮 record_outcome（或等价）写入 Intent 仓
