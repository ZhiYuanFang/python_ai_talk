## ADDED Requirements

### Requirement: Yield thinking before executing each preparation step
对于 clinic、tip 以及 intent 冷启动流式路径中的每个数据准备（或意图）节点，系统 SHALL 先通过 SSE 发送对应的 thinking 事件，再执行该节点逻辑。

#### Scenario: Clinic step order
- **WHEN** 客户端调用 `/v1/clinic/stream` 且进入数据准备阶段
- **THEN** 对每一个将执行的准备节点，thinking 事件的发送时刻 SHALL 早于该节点逻辑开始执行

#### Scenario: Tip step order
- **WHEN** 客户端调用 `/v1/tip/stream` 且进入数据准备阶段
- **THEN** 对每一个将执行的准备节点，thinking 事件的发送时刻 SHALL 早于该节点逻辑开始执行

#### Scenario: Intent stream step order
- **WHEN** 客户端调用 `/v1/analyze/intent/stream` 且走冷启动图路径
- **THEN** 对每一个将执行的意图/数据节点，thinking 事件的发送时刻 SHALL 早于该节点逻辑开始执行

### Requirement: Do not rely on post-completion updates for step thinking
流式路径 SHALL NOT 仅以 LangGraph `astream(stream_mode="updates")` 的节点完成事件作为「当前步 thinking」的唯一触发方式（该方式天然在执行之后）。

#### Scenario: Stream path uses explicit pre-step emission
- **WHEN** 实现 clinic/tip/intent 流式数据准备推进
- **THEN** 实现 SHALL 在调用节点函数之前发出该步 thinking（显式步进或等价机制）

### Requirement: Clinic implicit feedback announces before running
当 clinic 流式请求需要执行隐式建议采纳判定时，系统 SHALL 先发送 thinking，再执行判定逻辑。

#### Scenario: Feedback judge is announced
- **WHEN** 会话存在未处理的 last_suggestion 且将运行隐式判定
- **THEN** 客户端先收到相关 thinking，再进入判定耗时逻辑

### Requirement: Conditional intent routing preserved
intent 流式步进 SHALL 保持与现有意图图一致的分支语义（向量后路由、分类后路由至 history / clinic agent / end 等）。

#### Scenario: Feeding path still ends without clinic prep chain
- **WHEN** 冷启动意图分类结果为 feeding（或向量高置信直接结束路径）
- **THEN** 流式步进 SHALL NOT 错误地强制跑完 history/clinic 全链

### Requirement: SSE event shape unchanged
本能力 SHALL NOT 改变既有 SSE 事件类型字段约定（如 thinking / answer / done 及 intent answer JSON 包装方式）。

#### Scenario: Clients keep parsing same event types
- **WHEN** 升级后客户端仍按原 type 字段解析流
- **THEN** 事件仍可被识别为 thinking 或 answer（或 done），无需新必填字段
