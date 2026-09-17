## ADDED Requirements

### Requirement: Companion session without tip opening

陪伴会话 SHALL 仅由 clinic（及未来非 tip 入口）读写近轮对话。系统 MUST NOT 再提供 tip 开场写入 companion session 的路径。

#### Scenario: Tip does not append companion turns

- **WHEN** Python tip 模块已删除
- **THEN** 不存在 tip 路由向 companion_session 追加开场轮次的代码路径
