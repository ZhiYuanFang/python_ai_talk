## ADDED Requirements

### Requirement: tip agent 保持退役
系统 MUST NOT 恢复 tip SSE agent 或 `/device/tip/generate`。widget tip 展示路径可保留且 MUST NOT 依赖 tip agent。

#### Scenario: tip 路由不存在
- **WHEN** 客户端请求已删除的 tip 生成接口
- **THEN** 系统 MUST 返回不存在或等价失败
- **AND** MUST NOT 回退到 Python tip 图或 Gateway tip agent
