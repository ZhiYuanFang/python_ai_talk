## ADDED Requirements

### Requirement: 使用 RunnableConfig 传递 thread_id
意图分析的 `ainvoke` / `astream` SHALL 通过 `config={"configurable": {"thread_id": <id>}}` 传递检查点线程 ID，不得使用顶层关键字参数 `thread_id=`。

#### Scenario: 非流式调用不因 thread_id 崩溃
- **WHEN** 客户端调用意图分析非流式接口且图已编译带 checkpointer
- **THEN** 图执行 SHALL NOT 抛出 `unexpected keyword argument 'thread_id'`
- **AND** 检查点 SHALL 关联到该 thread_id

#### Scenario: 流式调用同样使用 config
- **WHEN** 客户端调用意图分析流式接口
- **THEN** `astream` SHALL 使用相同的 `configurable.thread_id` 形式

### Requirement: MemorySaver 检查点
意图图 SHALL 使用 `MemorySaver` 作为 checkpointer 编译，使 `interrupt()` 能够按 thread_id 保存与恢复状态。

#### Scenario: 中断后状态可恢复
- **WHEN** `prepare_confirm` 调用 `interrupt(...)` 且传入有效 thread_id
- **THEN** 图执行 SHALL 暂停
- **AND** 使用同一 thread_id 的 `Command(resume=...)` SHALL 能从中断点继续

### Requirement: Confirm 使用 Command resume
确认反馈接口 SHALL 使用 `ainvoke(Command(resume=user_feedback), config={"configurable": {"thread_id": conversation_id}})` 恢复图，不得调用不存在的 `intent_graph.confirm_intent` 方法。

#### Scenario: 用户确认后继续执行
- **WHEN** 客户端提交 `conversation_id` 与 `user_feedback=confirm`（或等价确认值）
- **THEN** 图 SHALL 从 `prepare_confirm` 恢复并进入 `handle_feedback`
- **AND** 飞轮或清理逻辑 SHALL 按反馈执行

#### Scenario: 用户拒绝后继续执行
- **WHEN** 客户端提交拒绝反馈
- **THEN** `handle_feedback` SHALL 执行拒绝路径
- **AND** 图 SHALL 正常结束并返回意图结果

### Requirement: 真实确认节点接线
意图图 SHALL 注册 `nodes/prepare_confirm.py` 与 `nodes/handle_feedback.py`，边为 `prepare_confirm → handle_feedback → END`，不得使用图内无 interrupt 的 stub 节点作为确认实现。

#### Scenario: 中断载荷含确认信息
- **WHEN** 进入真实 `prepare_confirm` 并触发 interrupt
- **THEN** 返回状态的 `__interrupt__`（或路由提取结果）SHALL 包含 `need_confirm`、`confirm_message`、`conversation_id`
