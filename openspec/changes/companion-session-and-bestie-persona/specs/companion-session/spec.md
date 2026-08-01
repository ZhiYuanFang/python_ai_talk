## ADDED Requirements

### Requirement: Session keyed by device_no
系统 SHALL 以 `device_no` 作为陪伴会话的唯一主键，在 Python 侧持久化 tip 与 clinic 共享的对话状态。

#### Scenario: Tip and clinic share one session
- **WHEN** 同一 `device_no` 先调用 tip 流式接口再调用 clinic 流式接口
- **THEN** clinic 生成回答时可读取到该 tip 开场所在会话中的近期轮次

#### Scenario: Different devices are isolated
- **WHEN** 两个不同的 `device_no` 分别产生 tip 或 clinic 对话
- **THEN** 各自会话互不可见

### Requirement: Persist session in Redis with 7-day TTL
系统 SHALL 将会话存储在 Redis 中，TTL 为 7 天，并在成功写入会话后滑动续期。

#### Scenario: Session survives process restart within TTL
- **WHEN** 会话已写入且未超过 7 天无成功写入
- **THEN** Python 进程重启后仍可按 `device_no` 读回该会话

#### Scenario: Expired session starts fresh
- **WHEN** 会话超过 TTL 未获续期
- **THEN** 下一次 tip 或 clinic 请求按空会话处理并创建新会话数据

### Requirement: Keep at most five turns
系统 SHALL 每个会话最多保留最近 5 轮对话；一轮包含一条 user 消息与一条 assistant 消息；超出时删除最旧的整轮。

#### Scenario: Sixth turn drops the oldest
- **WHEN** 会话已有 5 轮且再次成功追加 1 轮
- **THEN** 会话中仅保留最新的 5 轮

### Requirement: Tip opening writes a full turn
系统 SHALL 在 tip 流式回答成功生成后，向该 `device_no` 会话追加一轮：user 为基于事件名的合成开场（表明刚记录了该事件），assistant 为 tip 全文，并更新待判定建议元数据（含 answer_id 与本轮 knowledge_ids，若有）。

#### Scenario: Tip appends synthetic user plus assistant
- **WHEN** tip 流式接口为某 `device_no` 与 `event_name` 生成完整回答
- **THEN** 会话新增 1 轮，且 user 内容包含该事件名语义，assistant 内容为 tip 回答文本

### Requirement: Clinic appends real user and assistant turns
系统 SHALL 在 clinic 流式回答成功生成后，向该 `device_no` 会话追加一轮：user 为本次 `question`，assistant 为本次回答全文，并更新待判定建议元数据。

#### Scenario: Clinic continue after tip
- **WHEN** 会话中已有 tip 开场轮次，用户以同一 `device_no` 调用 clinic 并成功得到回答
- **THEN** 会话在 tip 轮次之后追加本轮 user/assistant，且总轮数不超过 5

### Requirement: Inject recent turns into generation context
系统 SHALL 在 tip 与 clinic 生成面向用户的回答时，将会话中近最多 5 轮对话注入提示上下文；喂养历史数据需求判断 SHALL NOT 将聊天轮次当作喂养事件历史。

#### Scenario: Clinic prompt includes prior tip turn
- **WHEN** clinic 为已有 tip 开场的 `device_no` 生成回答
- **THEN** 供 LLM 使用的上下文包含该 tip 轮次的内容摘要或全文（受 5 轮窗口限制）
