## REMOVED Requirements

### Requirement: Care Alert 飞轮仓
**Reason**: Care Alert 不再做数据飞轮；避免前端直打 Python 与 Go 转发飞轮。
**Migration**: 删除 Care 飞轮实现与反馈链；出卡改 Gateway 结构化 tool（见 `care-alert-gateway-cards`）。

## MODIFIED Requirements

### Requirement: 飞轮仅我方托管且分仓隔离
系统 SHALL 仅托管 **Intent** 与 **Clinic** 两套飞轮仓，彼此 MUST NOT 互相写入。Care Alert MUST NOT 拥有飞轮仓。飞轮基址 MUST 锁定我方，MUST NOT 随业务 BYO API 覆盖。飞轮 retrieve/record MUST 仅由 Gateway 对应 agent 经 tools 调用；Go MUST NOT 参与。

#### Scenario: 两仓隔离
- **WHEN** Intent agent 写入飞轮
- **THEN** 写入 MUST 进入 Intent 仓
- **AND** MUST NOT 写入 Clinic 仓或任何 Care 仓

#### Scenario: Go 不调用飞轮
- **WHEN** 任意 Go 业务请求完成
- **THEN** 该路径 MUST NOT 发起飞轮 HTTP/RPC
