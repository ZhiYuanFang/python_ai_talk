## Why

clinic / tip / intent 流式接口用 `astream(stream_mode="updates")`，thinking 在**节点执行完成后**才推送；再叠加 clinic 隐式飞轮前的静默段，前端常感到「思考字幕一下子全出来」，无法体现「执行到哪一步」。需要改为先推 thinking、再执行该步逻辑。

## What Changes

- 流式路径改为逐步执行：对每一步 **先 yield thinking SSE，再 await 节点**，合并 state 后进入下一步
- 覆盖 **`/v1/clinic/stream`、`/v1/tip/stream`、`/v1/analyze/intent/stream`**（冷启动走图的路径）
- clinic：隐式飞轮若执行，亦先推 thinking 再判定
- intent：按现有条件路由手写步进（复用 `_route_after_*`），非流式 `/intent` 可继续 `ainvoke`
- tip/clinic：线性数据准备步进；LLM 流式生成前仍推 `llm_start` thinking
- **不**改变 SSE 事件类型契约（仍为 thinking / answer / done 等）；**不**删除已编译 graph（可供非流式或回退）

## Capabilities

### New Capabilities

- `progressive-stream-thinking`: 流式接口逐步「先思考字幕、再执行节点」的行为要求

### Modified Capabilities

- （无：`openspec/specs/` 下无已归档基线）

## Impact

- **代码**：`app/api/routes/clinic.py`、`tip.py`、`intent.py`；可选 `app/shared` 线性步进辅助；intent 路由函数复用
- **API**：路径与字段不变；thinking 到达时机提前、按步间隔出现
- **跨仓**：Go/Flutter 若按行消费 SSE 即可受益；无需新字段
