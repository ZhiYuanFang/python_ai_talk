# Design: fix-confirm-flow-resume

## 架构概览

### 修复前的 confirm 流程（断裂）

```
用户请求 → /v1/analyze/intent
  ↓
intent_graph.ainvoke(initial_state)  ← 没传 thread_id
  ↓
match_event_by_vector (置信度 90%-95%)
  ↓
prepare_confirm
  ↓ 返回 {need_confirm, confirm_message}  ← 没有 conversation_id
  ↓
→ END  ← 直连 END，handle_feedback 孤儿
  ↓
路由层返回 IntentResponse(need_confirm=True, conversation_id="")

用户确认 → /v1/analyze/intent/confirm
  ↓
intent_graph.confirm_intent(conversation_id="", user_feedback)
  ↓
ainvoke({"user_feedback": "confirm"}, config={thread_id: ""})  ← thread_id 为空
  ↓
MemorySaver 找不到检查点  ← 无法恢复
  ↓
失败/无响应
```

### 修复后的 confirm 流程（interrupt + Command 恢复）

```
用户请求 → /v1/analyze/intent
  ↓
thread_id = uuid4()  ← 路由层生成
  ↓
intent_graph.ainvoke(initial_state, thread_id=thread_id)
  ↓
match_event_by_vector (置信度 90%-95%)
  ↓
prepare_confirm
  ↓ 生成 conversation_id = thread_id
  ↓ 调用 interrupt({"need_confirm": True, "confirm_message": "...", "conversation_id": "..."})
  ↓ 图执行暂停，状态保存到 MemorySaver[thread_id]
  ↓ interrupt 返回 None（中断时）
  ↓
ainvoke 返回中断状态（包含 __interrupt__ 字段）
  ↓
路由层从中断状态提取 need_confirm/confirm_message/conversation_id
  ↓
返回 IntentResponse(need_confirm=True, confirm_message="...", conversation_id=thread_id)

用户确认 → /v1/analyze/intent/confirm
  ↓
intent_graph.ainvoke(Command(resume=user_feedback), thread_id=conversation_id)
  ↓
图从 prepare_confirm 的 interrupt 处恢复
  ↓ interrupt() 返回 user_feedback（"confirm" 或 "reject"）
  ↓ prepare_confirm 返回 {"user_feedback": user_feedback}
  ↓
handle_feedback  ← 现在有入边了（prepare_confirm → handle_feedback）
  ↓ 执行数据飞轮（confirm）或删除向量（reject）
  ↓
→ END
  ↓
路由层返回最终 IntentResponse
```

## 核心设计决策

### 1. interrupt() 函数的位置

在 `prepare_confirm` 节点内部调用 `interrupt()`，而非在 `intent_graph.py` 中使用 `interrupt_before`/`interrupt_after` 配置。

**理由**：
- `interrupt()` 函数式调用更灵活，可以在节点内部根据条件决定是否中断
- 可以在中断时传递结构化数据（need_confirm、confirm_message、conversation_id）
- LangGraph 0.2.x 推荐使用 `interrupt()` 函数而非配置式中断

### 2. conversation_id 与 thread_id 的关系

**决策**：`conversation_id = thread_id`，在路由层生成。

**理由**：
- LangGraph 的检查点恢复依赖 thread_id
- 客户端需要一个 conversation_id 来调用 confirm 接口
- 两者统一，避免维护两套 ID 的映射关系
- 路由层生成 ID，确保在图执行前就确定

### 3. prepare_confirm → handle_feedback 的边

**决策**：将 `prepare_confirm → END` 改为 `prepare_confirm → handle_feedback`。

**理由**：
- interrupt 恢复后，prepare_confirm 节点继续执行剩余代码并返回状态
- 下一个节点应该是 handle_feedback（处理用户反馈）
- handle_feedback 执行数据飞轮或删除向量后，再 → END

### 4. 流式接口的中断处理

**决策**：astream 在遇到 interrupt 时会自然停止 yield，路由层检测到流结束后，从中断状态提取确认信息。

**实现**：
- astream 遍历结束后，检查 final_state 中是否有 `__interrupt__` 字段
- 如果有，说明图被中断，提取 interrupt 的值作为确认信息
- 推送 answer 事件包含 need_confirm=True

### 5. confirm 接口的 Command 恢复

**决策**：confirm 接口使用 `Command(resume=user_feedback)` 恢复图执行。

**实现**：
```python
from langgraph.types import Command

# 恢复中断的图执行
final_state = await intent_graph.ainvoke(
    Command(resume=request.user_feedback),
    thread_id=request.conversation_id,
)
```

## 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `app/feeding/graphs/nodes/prepare_confirm.py` | 1. 生成 conversation_id（从 state 的 thread_id 获取或生成 uuid4）<br>2. 调用 `interrupt()` 中断图执行<br>3. interrupt 恢复后返回 user_feedback |
| `app/feeding/graphs/intent_graph.py` | 1. 将 `prepare_confirm → END` 改为 `prepare_confirm → handle_feedback`<br>2. 添加 `handle_feedback → END` 边 |
| `app/api/routes/intent.py` | 1. 非流式：生成 thread_id，传给 ainvoke<br>2. 从中断状态提取确认信息<br>3. confirm 接口用 `Command(resume=...)` 恢复<br>4. 流式：生成 thread_id，传给 astream<br>5. 流式：从中断状态提取确认信息 |
| `app/feeding/graphs/states/intent_state.py` | 无需修改（conversation_id 和 user_feedback 字段已存在） |

## interrupt() 函数行为详解

### 中断时
```python
from langgraph.types import interrupt

async def prepare_confirm(state):
    # ... 构造确认信息 ...
    # 调用 interrupt，图执行暂停
    # interrupt 的参数会被保存到检查点，并通过 ainvoke 的返回值暴露给调用方
    user_feedback = interrupt({
        "need_confirm": True,
        "confirm_message": confirm_message,
        "conversation_id": conversation_id,
    })
    
    # 这行代码在 interrupt 恢复后才会执行
    # user_feedback 是 Command(resume=...) 传入的值
    return {"user_feedback": user_feedback, "conversation_id": conversation_id}
```

### 恢复时
```python
from langgraph.types import Command

# 恢复中断的图执行
# Command(resume=value) 中的 value 会作为 interrupt() 的返回值
final_state = await graph.ainvoke(
    Command(resume="confirm"),  # 用户确认
    config={"configurable": {"thread_id": conversation_id}},
)
```

### 中断状态的检测
```python
# ainvoke 返回的状态中，如果有 __interrupt__ 字段，说明图被中断
final_state = await graph.ainvoke(state, config={"configurable": {"thread_id": thread_id}})

# 检查是否中断
interrupts = final_state.get("__interrupt__", [])
if interrupts:
    # 图被中断，提取 interrupt 的值
    interrupt_value = interrupts[0].value  # interrupt() 的参数
    need_confirm = interrupt_value.get("need_confirm", False)
    confirm_message = interrupt_value.get("confirm_message", "")
    conversation_id = interrupt_value.get("conversation_id", "")
```
