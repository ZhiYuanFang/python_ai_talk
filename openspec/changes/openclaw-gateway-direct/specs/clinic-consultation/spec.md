## REMOVED Requirements

### Requirement: Clinic 显式 feedback 飞轮入口
**Reason**: Clinic 仅保留 Gateway agent 内隐式采纳；禁止 App/Go 显式点赞写飞轮。
**Migration**: 删除 `/device/api/clinic/feedback` 与 Python `/v1/clinic/feedback`；Flutter 去掉显式赞调用。

## MODIFIED Requirements

### Requirement: Clinic 经 Gateway 只读陪伴
Clinic 陪伴 SHALL 由 OpenClaw Gateway Clinic agent 提供。对 Go 的主返回为自然语言（可流式）。Clinic MUST NOT 挂载历史写 tools。隐式采纳若发生，MUST 仅在 agent 回合内经 Clinic 飞轮 tool 完成。

#### Scenario: 无显式赞
- **WHEN** 用户继续 Clinic 对话
- **THEN** 系统 MUST NOT 要求客户端先调 clinic feedback 接口才能完成学习
- **AND** 学习 MUST NOT 经 Go 转发
