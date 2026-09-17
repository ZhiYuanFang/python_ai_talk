## ADDED Requirements

### Requirement: Python tip module and API removed

Python 服务 MUST NOT 再提供 tip agent（`app/tip` 图/节点/提示词）及 `POST /v1/tip/stream`（或等价 tip 流式路由）。路由汇总 MUST NOT 挂载 tip router。

#### Scenario: Tip stream route absent

- **WHEN** 客户端请求 `POST /v1/tip/stream`
- **THEN** 本服务 MUST NOT 将该路径注册为有效业务路由

#### Scenario: Tip package absent from runtime imports

- **WHEN** 检查应用路由与图注册
- **THEN** MUST NOT 再 import 或 compile `tip_graph` 作为存活入口
