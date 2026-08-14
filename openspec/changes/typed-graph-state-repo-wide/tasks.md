## 1. 共享合并与 Protocol

- [x] 1.1 在 `shared/graphs` 实现 `apply_state_patch`（Pydantic `model_copy(update=...)` 或等价），供 stream / ainvoke 边界使用；中文注释说明不丢未提及字段
- [x] 1.2 改造 `stream_graph` / `node_thinking`：终态合并走补丁助手，保持与非流式语义一致
- [x] 1.3 为共享节点定义 Protocol（如 device_no、data_requirement、event_dictionary、history_events、baby_profile），调整 `fetch_*` / `judge_*` / `search_vectors` / `derive_baby_age` / `history_gate` 签名，禁止导入业务 State 类

## 2. 四图 Pydantic State

- [x] 2.1 `IntentState`、`ClinicState`、`TipState`、`CareAlertState` 改为 Pydantic BaseModel，字段集与现网对齐（含 event_dictionary 等通道）
- [x] 2.2 四图 `StateGraph(...)` 注册新 State；路由 / care-alert analyze 入口改为模型构造赋值

## 3. 核心嵌套模型

- [x] 3.1 新增 `IntentResult`、`DataRequirement`（放置于 feeding/shared 合适模块，避免 feeding↔clinic 互引）；care-alert `items` 钉为既有 DTO 列表类型
- [x] 3.2 意图路径：`classify_intent` / `resolve_remark_event` / cache / pipeline / 确认 主路径改用 `IntentResult`
- [x] 3.3 clinic/tip/care-alert：`judge_data_requirement` 与 `fetch_history` 主路径改用 `DataRequirement`

## 4. 节点属性化收尾

- [x] 4.1 意图图各节点：`.get` 主路径改为属性访问，返回字段补丁
- [x] 4.2 clinic / tip / care-alert 图节点同样属性化与补丁返回
- [x] 4.3 清理无用 TypedDict 表述与匿名 dict 主路径构造；保留边界 `model_dump` 若 LangGraph 需要并加注释

## 5. 手工验收

- [x] 5.1 intent：分类 + 备注反查（唯一/多命中/零命中）+ 确认续聊；流式与非流式关键字段一致
- [x] 5.2 clinic / tip：注入非空 `event_dictionary` 后 judge 可见，不误报空
- [x] 5.3 care-alert analyze：拉史 + 产出 items；对照规格无行为回归
