## Why

四图 State 已迁为 Pydantic，但部分共享函数与业务节点仍注解为 `Dict[str, Any]` 并用 `state.get` / `key in state` 读取。传入模型实例时会运行时失败或静默读不到字段；注解也与真实类型脱节。需对齐既有约定：吃整包 State 的入口用 `Any`，读字段走 `state_get`。

## What Changes

- 扫修 `app/shared` 中签名含 `state` 的公开 API：凡仍为 `Dict[str, Any]` + `.get` 的，改为 `Any` + `state_get`（含 `is_block_fast_path`、`derive_history_grounded`；遗留 `progressive_thinking` 同步对齐读/写约定）。
- 扫修 clinic / tip / care_alert 中仍写 `state: Dict[str, Any]` 的图节点与同路径辅助函数：注解改为 `Any`；仍用 `.get` / `in state` 读字段的改为 `state_get`。
- **不**改变对外 API、图拓扑或业务判定语义；feeding 已基本 `Any` + `state_get`，本变更以对齐为准。
- **不**为共享层引入具体业务 State 类导入（避免 feeding↔clinic 互引）。

## Capabilities

### New Capabilities

- `graph-state-access`: 约定图 State 访问方式——共享层与图节点入参 `state: Any`，读字段经 `state_get`；禁止以假 `Dict` 注解冒充 Pydantic State。

### Modified Capabilities

- （无。本变更落实 typed-graph-state 收版后的访问约定缺口，不修改既有 capability 的对外行为需求。）

## Impact

- **代码**：`app/shared/qa_fast_path.py`、`app/shared/companion_session.py`、`app/shared/progressive_thinking.py`；clinic 节点（含 `search_qa_fast_path`、`format_qa_answer`、`resolve_clinic_needs_history` 等）；tip `stream_tip_response`；care_alert `generate_care_alerts`、`resolve_baby_age`。
- **API / 契约**：无对外 HTTP 契约变更。
- **风险**：漏改的 `.get` 在 Pydantic 路径上仍可能 AttributeError；tasks 以全仓 `state: Dict` / 节点内 `state.get` 清单验收。
