## Why

流式路径为「先报后做」手搓了与 LangGraph 平行的步进表，和非流式 `ainvoke` 双轨维护边与条件（门禁、skip_knowledge 等已显形分叉）。当初以为只能放弃逐步 thinking 才能统一编排；实际上 LangGraph `stream_mode=custom` + 节点内 `get_stream_writer` 可在节点真正干活前推送 thinking，从而 **一套图同时服务流式逐步字幕与非流式 ainvoke**。

## What Changes

- clinic / tip / intent 流式数据准备（及 intent 冷启动图路径）改为驱动已编译图的 `astream`（含 `custom`），不再用路由层第二份 `prepare_steps` / 手写 `route_after_*` 循环执行准备节点
- 节点（或统一包装）在执行业务逻辑前经 stream writer 发出逐步 thinking；非流式继续 `ainvoke`，不消费 custom
- 保留 progressive 产品语义：执行到哪步先出哪步字幕；SSE 事件类型不变（thinking / answer / done）
- 隐式飞轮等图外步骤：迁入图或保留入口单次 thinking，避免再出现「图外静默 + 图内双轨」
- 最终回答 token 流仍在图外（或等价生成阶段），与准备编排分离
- 处理嵌套：`call_clinic_agent` → clinic 准备须能向外冒泡 custom thinking，或合并为可观测的同一流式边界
- 清理或收窄 `progressive_thinking` 路由步进用法（可保留工具函数若仍有价值）
- 替代/ supersede 手搓方案作为「唯一能先报后做」的实现路径（产品要求保留，实现换成 LangGraph custom）

## Capabilities

### New Capabilities

- `langgraph-unified-stream`: 流式与非流式共用同一 LangGraph 编排；流式经 custom 事件输出逐步 thinking，非流式 ainvoke 忽略之

### Modified Capabilities

- （无主库 `openspec/specs/` 基线；与 `progressive-stream-thinking` / `clinic-needs-history-gate` 行为对齐由本 change 新 spec 约束）

## Impact

- 路由：`clinic.py`、`tip.py`、`intent.py` 流式生成器
- 图：`clinic_graph`、`tip_graph`、`intent_graph`；共享节点或 thinking 包装；`call_clinic_agent` 嵌套流
- 辅助：`progressive_thinking.py`、thinking_messages 映射
- API：路径与 SSE 字段不变；thinking 仍按步出现，但驱动源改为图 custom 流
- 依赖：现有 langgraph（项目 Python 3.12，可用 async `get_stream_writer`）
