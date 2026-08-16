## ADDED Requirements

### Requirement: 删除 tip Agent 全链路
系统 SHALL 删除 tip（事件开场陪伴）智能体能力，包括 Python `/v1/tip` 路由与 `app/tip` 模块、Go `TipStream`/`TipCtrl`/`POST /device/tip/generate` 及仅为 tip 服务的 feedback/反代（若无其它调用方）、Flutter 中 tip SSE 客户端死代码（`TipRepository`、`tip_provider`、`HomeTipPanel` 等）。系统 MUST NOT 再提供 tip Agent 作为 OpenClaw/产品面能力。

#### Scenario: Python tip 路由不存在
- **WHEN** 客户端请求原 `/v1/tip/stream`（或等价 tip 入口）
- **THEN** 服务 MUST NOT 再提供该 tip 生成能力（404 或路由未注册）

#### Scenario: Flutter 无 tip SSE 调用
- **WHEN** 审查 App 主路径
- **THEN** MUST NOT 再调用 `/device/tip/generate` SSE 作为首页开场

### Requirement: 保留 widget tip 产品面
删除 tip Agent MUST NOT 删除 Flutter `widget_tip_*` 及由 Care Alert/预测同步产生的桌面或预测页贴士文案能力。该能力 MUST 视为 Care Alert/小组件产品面，MUST NOT 重新实现为 tip Agent。

#### Scenario: widget tip 缓存仍可用
- **WHEN** 护理留意或预测同步写入小组件 tip 文案
- **THEN** App MUST 仍能读取 `widget_tip_*` 类缓存用于展示或注入陪伴
- **AND** MUST NOT 依赖已删除的 tip SSE Agent
