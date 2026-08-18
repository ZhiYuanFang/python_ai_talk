## Context

`typed-graph-state-repo-wide` 已将四图主路径 State 迁为 Pydantic，并引入 `state_get` / `apply_state_patch`。共享节点（`fetch_history` 等）与 feeding 意图节点大多已是 `state: Any` + `state_get`。遗漏集中在：

- shared：`is_block_fast_path`、`derive_history_grounded`、遗留 `progressive_thinking`
- clinic / tip / care_alert：若干节点仍标 `Dict[str, Any]`；其中部分体内仍 `state.get` / `key in state`

约束：禁止 feeding↔clinic 互引；共享层不得 import 业务 State 类；行为语义不变。

## Goals / Non-Goals

**Goals:**

- 统一「整包 State 入参」为 `Any`，读字段统一 `state_get`。
- 清掉清单内假 `Dict` 注解与不安全 `.get` / `in state`。
- 遗留 `progressive_thinking`：签名与合并方式与 Pydantic 兼容（读用 `state_get`，写用 `apply_state_patch`），避免再 `dict.update` 假定。

**Non-Goals:**

- 不为共享层引入 Protocol / 具体 `ClinicState` 类型钉死（`Any` + `state_get` 已满足跨图与模块分离）。
- 不合并重复门禁逻辑（如 `resolve_clinic_needs_history` 与 `should_fetch_history` 语义相近，本变更只改访问方式）。
- 不改图拓扑、提示词内容、对外 API。
- 不写测试文件。

## Decisions

### 1. 注解统一为 `Any`，不用具体 State 类

- **选择**：图节点与 shared 读 State 的公开函数一律 `state: Any`。
- **理由**：与 feeding / 共享节点现状一致；避免 shared→clinic 类型依赖；跨图复用无摩擦。
- **备选**：节点写 `ClinicState` / `TipState` — 类型更严，但本仓混合调用面大，且与「共享不绑业务 State」冲突；本变更不采用。

### 2. 读字段只走 `state_get`

- **选择**：禁止对整包 State 使用 `.get` / `key in state`（Mapping 假定）。
- **理由**：Pydantic 无 `.get`；`in state` 对模型语义也不稳定。
- **例外**：补丁 dict、候选 metadata、LLM JSON 解析结果等**非图 State** 仍可用 `.get`。

### 3. `progressive_thinking` 一并修，不单独开 change

- **选择**：`state: Any`；步进合并改 `apply_state_patch`；`NodeFn` 入参类型同步放宽。
- **理由**：模块标注遗留但仍在仓库内，假 Dict + `update` 与基线冲突；修成本低。
- **备选**：仅改注释标明「仅 dict」— 易再被误用，否决。

### 4. care_alert `resolve_baby_age` 的 preset 读取

- **选择**：用 `state_get(state, "baby_age_months")` 替代 `"baby_age_months" in state and state.get(...)`。
- **理由**：预置月龄在模型上总是「有字段」；应用值是否为 None 判断即可。

## Risks / Trade-offs

- **[Risk] 漏改导致运行时 AttributeError** → 实现后对 `app/` 再 grep `state: Dict\[str, Any\]` 与节点内 `state\.get(`；tasks 列清单勾选。
- **[Risk] `Any` 削弱静态检查** → 接受；与现有共享节点一致。后续若要 Protocol 可另开 change。
- **[Trade-off] 不抽公共门禁函数** → 短期重复逻辑仍在；避免本变更膨胀。

## Migration Plan

- 纯类型与读法对齐，无数据迁移；部署即生效。
- 回滚：还原本 change 触及文件即可。

## Open Questions

- （无。注解 `Any` vs 具体 State、是否纳入 progressive_thinking / 节点假 Dict，探索阶段已拍板。）
