## Context

四图 State 均为 `TypedDict`，运行时仍是 dict；节点与路由大量 `Dict[str, Any]` + 字符串 key。共享节点（`fetch_history` 等）靠鸭子 `.get`。流式路径 `stream_graph` 用 `dict.update` 合并补丁。意图路径另有 `intent_result: Dict[str, Any]`；clinic/tip 有 `data_requirement` 自由字典。

约束：feeding 不得导入 clinic；中文注释；不写测试；对外 API JSON 行为不变。刚落地的备注反查（`resolve_remark_event`、消歧 pending）仍触达 `intent_result` 字典，迁模型时必须一并改写。

## Goals / Non-Goals

**Goals:**

- 四图 State 统一为 Pydantic BaseModel；入口构造、属性读取。
- shared 节点用 Protocol；stream / thinking 合并不丢字段。
- `IntentResult`、`DataRequirement` 模型化（核心 B）。
- care_alert `items` 钉为既有 DTO 类型。

**Non-Goals:**

- 不改变用户可见 CRUD / 陪伴 / tip / care-alert 语义。
- 不把 clinic 全部 QA 标量收成嵌套大模型（保持 State 顶层字段即可）。
- 不强制节点原地 mutate 整对象作为唯一写回方式。
- 不迁 Go 契约；不写测试。

## Decisions

### 1. State 载体：Pydantic BaseModel

- **选择**：`IntentState` / `ClinicState` / `TipState` / `CareAlertState` 改为 Pydantic（`model_config` 允许额外忽略或显式字段集，与现有请求模型风格一致）。
- **原因**：与 `IntentRequest`/`IntentResponse` 一致；构造即校验；IDE 属性补全。
- **备选否决**：dataclass（少校验、与 API 层风格分裂）；继续 TypedDict（解决不了运行时字典味）。

### 2. 节点写回：返回字段补丁 dict

- **选择**：节点 `async def foo(state: XxxState) -> dict`，返回 `{字段名: 值}`；值若为嵌套模型则可为模型实例或 `model_dump()`，由统一合并层写入 State。
- **原因**：贴合 LangGraph 部分更新；避免「返回整对象却丢未列出字段」。
- **备选否决**：节点内 mutate `state.x = ...; return state` 作为唯一方式（与现网 wrapper / stream 合并不一致，易漏）。

### 3. 合并层：统一 `apply_state_patch(state, patch) -> State`

- **选择**：在 `shared/graphs` 提供补丁合并（Pydantic `model_copy(update=...)` 或等价），供 `stream_graph`、`ainvoke` 后处理、`node_thinking` 使用。嵌套 `IntentResult`/`DataRequirement` 若补丁给的是 dict，则解析/合并进模型，禁止静默丢掉已有非 None 字段（除非补丁显式覆盖）。
- **原因**：四处手写 `dict.update` 是丢 `event_dictionary` 的历史根因之一。

### 4. 共享节点：Protocol，不放巨无 BaseState

- **选择**：例如 `HasDeviceNo`、`HasDataRequirement`、`HasEventDictionary`；`fetch_history(state: HasDeviceNo, ...)` 等用结构子类型。
- **原因**：四图字段不全相同；Protocol 保持模块边界。
- **备选否决**：一个 `AppGraphState` 上帝对象。

### 5. 核心 B 嵌套模型

- **`IntentResult`**：覆盖当前意图图主路径字段（`op`/`action`/`target_type`/`event_id`/`event_name`/`event_ids`/`events`/`remark_keyword`/`missing_events`/`quantity`/`content`/`need_confirm`/`confirm_*` 等）；LLM JSON 先 `model_validate`（允许额外字段 ignore），再规则改写。
- **`DataRequirement`**：`event_ids`/`time_range`/`start_time`/`end_time`/`limit`/`remark` 等 judge/fetch 已用字段。
- **care_alert `items`**：`List[CareAlertItemDto]`（或等价已有 schema）。
- **原因**：intent 中段可读性主要卡在 `intent_result`；`data_requirement` 是 clinic/tip/care 共享脏点。

### 6. 入口禁止匿名 dict 主路径

- **选择**：路由写 `IntentState(user_input=..., device_no=..., ...)`；若 LangGraph 需要 dict，仅在边界 `model_dump()` 一次并在注释标明「仅序列化边界」。
- **原因**：满足「对象赋值」的可读性诉求。

### 7. 与备注反查的衔接

- **选择**：`resolve_remark_event` / `clarification` / `intent_pipeline` 读写 `IntentResult` 属性或经小型 helper；多命中消歧仍写 pending，响应字段组装不变。
- **原因**：刚落地行为不得回归。

## Risks / Trade-offs

- [补丁合并漏嵌套] → 集中 `apply_state_patch` + 手工验 event_dictionary / intent_result 保留。
- [Protocol 与运行时仍是模型] → 共享节点用属性访问；若收到 dict（旧调用）在边界转模型一次。
- [LLM JSON 字段漂移] → `IntentResult` extra=ignore；缺省与现网 `setdefault` 对齐。
- [改动面大] → 单 change 分任务：先合并层+四 State，再嵌套模型，再逐图改节点。
- [无测试] → tasks 含四条主路径手工清单。

## Migration Plan

1. 只发 Python 镜像。
2. 回滚：回退镜像即可（无 DB 迁）。
3. 建议实现顺序见 tasks：shared 合并 → 四 State → 嵌套模型 → 节点/路由 → 手工验收。

## Open Questions

- （无。档位 A+核心 B、Pydantic State、全仓四图已拍板。）
