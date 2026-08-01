## Context

三条流式路由均在 `async for chunk in *_graph.astream(..., stream_mode="updates")` 内，于节点**完成后** `yield` thinking。clinic 在 astream 前还有 `_maybe_apply_implicit_feedback`（可能调 LLM）且无字幕。产品要求：执行到哪步就先看到哪步的思考。

## Goals / Non-Goals

**Goals:**

- clinic / tip / intent(stream)：**先 thinking，再执行**该步
- clinic 飞轮段同样先报后做
- 保持现有 thinking 文案映射与 SSE 形状

**Non-Goals:**

- 不改非流式 `/intent`、`ainvoke` 主路径（除非顺带复用工具）
- 不强制删除 LangGraph 编译图
- 不解决 Go/网关缓冲（本 change 保证服务端按步 yield；透传另议）

## Decisions

### 1. 方案 A：路由层逐步 await，不用 updates 驱动字幕

- **选择**：流式生成器内显式步骤循环 / intent 步进器
- **理由**：唯一能保证「先报后做」；不依赖 astream 完成事件语义

### 2. tip / clinic：线性步骤表

clinic 数据准备：

1. （可选）implicit_feedback  
2. judge_data_requirement  
3. fetch_history  
4. search_vectors  
5. fetch_baby_profile  
6. llm_start → `stream_response`

tip：在 baby_profile 后加 `derive_baby_age`，再 `stream_tip_response`。

可抽 `async def iter_linear_steps(steps, state)`：对每步 yield 文案、await fn、update state。

### 3. intent：条件步进

- **选择**：冷启动 stream 不用 astream；顺序调用节点函数，分支调用现有 `_route_after_vector_match` / `_route_after_classify`（从 intent_graph 导出或移到可 import 模块）
- **理由**：图有条件边，死板列表不够
- pending / 精确父名短路径：可保持现行为（无多节点）；可选补一条短 thinking（非必须）

### 4. 图实例保留

- **选择**：`clinic_graph` / `tip_graph` / `intent_graph` 保留；流式改走节点函数直接调用
- **理由**：改动面可控，非流式与测试不炸

### 5. 刷新友好

- **选择**：每步 yield 后可 `await asyncio.sleep(0)` 让出事件循环（可选，利于真流式刷出）
- **理由**：减轻「同 tick 多条 yield」被客户端糊成一把的概率

## Risks / Trade-offs

- [与 graph 边定义漂移] → 步进顺序与路由函数与 graph 保持同一套符号；改图时同步步进
- [intent 步进漏分支] → 对照 `_route_after_*` 全分支写测试清单（手工回归）
- [透传仍缓冲] → 本仓按步 yield 后若仍一把到，查 Go；不阻塞本 change

## Migration Plan

1. 部署后直连 Python 验证 thinking 间隔
2. 回滚：恢复 astream 循环即可

## Open Questions

- 无（A + 三端已确认）
