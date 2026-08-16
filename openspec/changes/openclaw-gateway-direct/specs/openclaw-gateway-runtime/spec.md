## ADDED Requirements

### Requirement: Gateway 为唯一编排权威
系统 SHALL 使用真实 OpenClaw Gateway 作为 Intent、Clinic、Care Alert 的编排运行时。系统 MUST NOT 再以 Python 进程内步骤表（`run_agent_steps` 或等价迷你图）或 LangGraph `StateGraph` 作为上述三能力的编排权威。

#### Scenario: 意图回合经 Gateway
- **WHEN** Go 为设备用户发起一轮喂养/查记录对话
- **THEN** Go MUST 调用 OpenClaw Gateway 上的 Intent agent（而非 Python `/v1/analyze/intent`）
- **AND** Python MUST NOT 再作为该回合的编排入口

#### Scenario: 禁止伪 OpenClaw 达标
- **WHEN** 验收「已接入 OpenClaw」
- **THEN** 运行时 MUST 存在可配置的 Gateway 基址且实际发起 agent run
- **AND** 仅存在空的 `OPENCLAW_GATEWAY_URL` 或仅有进程内 step loop MUST NOT 视为达标

### Requirement: Go 注入 model
Go 在调用 Gateway 之前 SHALL 完成模型选型（含额度/VIP 策略），并将选定 model 注入该次 Gateway agent run。Gateway MUST 使用该注入 model（或明确失败），MUST NOT 在无 Go 注入时擅自改用与额度策略无关的默认商业模型作为正式计次路径。

#### Scenario: 计次在成功之后
- **WHEN** Gateway Intent/Clinic/Care 回合成功返回
- **THEN** Go MAY 按既有策略计次
- **AND** Go MUST NOT 因飞轮写入成功与否而改变计次（Go 无飞轮关系）

### Requirement: Session 承载澄清
Intent 澄清续轮 SHALL 使用 Gateway session（稳定 sessionKey，由 Go 映射 device/conversation）。系统 MUST NOT 再依赖 Python Redis pending + 响应字段 `need_confirm` 作为权威澄清协议。

#### Scenario: 同 session 追问
- **WHEN** Intent agent 因信息不足未调用写 tool 并回复追问
- **AND** 用户在同一 sessionKey 下继续补充
- **THEN** Gateway MUST 在该 session 上下文中继续 Intent agent 回合

### Requirement: 三 Agent 分区与写 ACL
系统 SHALL 配置三个 Gateway agent（Intent、Clinic、Care Alert）。Clinic 与 Care Alert 的 tool 策略 MUST NOT 允许历史写工具（create/update/delete/end）。仅 Intent MUST 被允许调用历史写工具。

#### Scenario: Clinic 无法写史
- **WHEN** Clinic agent 回合执行
- **THEN** 其可用 tools MUST NOT 包含 history create/update/delete/end
