## ADDED Requirements

### Requirement: Care Alert 经 Gateway 出卡
Care Alert SHALL 由 OpenClaw Gateway 上的 Care Alert agent 编排。生成结果的权威形态 SHALL 为结构化 tool 返回值（例如 emit care cards），包含卡片列表字段；Go MUST 从该 tool 结果写入日缓存或推送桌面，MUST NOT 将 assistant 自由文本解析为卡片权威。

#### Scenario: 日批出卡
- **WHEN** Go 触发护理留意日分析并注入 model 调用 Care Alert agent
- **THEN** 回合 MUST 产生结构化卡片列表 tool 结果
- **AND** Go MUST 能在不解析自由文本 JSON 的情况下取得 items

### Requirement: Care Alert 无数据飞轮
系统 MUST NOT 为 Care Alert 提供数据飞轮（包括 prompt 飞轮、feedback ledger、suggestion 快照归因闭环，以及 `/v1/care-alert/feedback` 或 Go 转发至飞轮的路径）。用户 ignore/follow_up 若保留，MUST 仅影响本地/日缓存展示，MUST NOT 触发学习写入。

#### Scenario: 无飞轮反馈链
- **WHEN** 用户在 App 忽略一张护理留意卡片
- **THEN** 系统 MUST NOT 调用 Python/飞轮服务记录 Care 学习样本
- **AND** Go MUST NOT 存在「转发 Care 反馈到飞轮」的业务路径

#### Scenario: 前端不直打 Python
- **WHEN** Flutter 或其他客户端处理 Care Alert
- **THEN** 客户端 MUST NOT 直接请求 Python Care/飞轮接口
