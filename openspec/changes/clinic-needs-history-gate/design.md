## Context

Clinic / tip / intent 共享数据准备链：`judge_data_requirement` → `fetch_history` →（可选）`search_vectors` → `fetch_baby_profile`。`judge_data_requirement` 只输出 event_ids / time_range / limit，默认假设需要历史；失败 fallback 为近 7 天全类型。clinic thinking 文案已写「要不要翻记录」，实现无门禁。

约束：不改对外 HTTP；门禁只影响喂养历史；tip 流式已硬编码 `data_requirement` 并跳过 judge；intent history 经 `call_clinic_agent` + `clinic_graph`，已有 `skip_knowledge` 条件边可作对称模式。

## Goals / Non-Goals

**Goals:**

- 拆出 `judge_needs_history`，先于范围判断与拉取
- 宽松策略：可能有用则 `needs_history=true`；失败/缺省默认 true
- `needs_history=false` 时跳过 `judge_data_requirement` 与 `fetch_history`，`history_events=[]`
- intent `history` 与 tip 强制需要历史（跳过门禁或 `force_needs_history`）
- clinic 图与流式步进、thinking 文案与三节点对齐

**Non-Goals:**

- 不为知识检索 / 宝宝画像增加同类门禁
- 不把 `needs_history` 塞进 `data_requirement` JSON
- 不改 tip 流式「硬编码范围 + 直拉 history」的主路径（仅明确不挂门禁）
- 不做启发式短路替代第一节点 LLM（可后续优化）

## Decisions

### 1. 拆节点，不扩 `judge_data_requirement`

- **选择**：`judge_needs_history` →（条件）→ `judge_data_requirement` → `fetch_history`
- **理由**：顺序与产品语义一致；false 时可省掉 scope LLM + history API；thinking 可分段
- **替代**：同节点加 `needs_history` 字段 — 少一次 LLM，但提示词与职责混杂，false 时仍付 scope 生成成本；已否决

### 2. 宽松门禁 + 失败默认 true

- **选择**：提示词指导「可能有用就 true」；解析失败、异常、缺字段 → true
- **理由**：宁可多拉，避免查记录/模式题漏数据
- **替代**：严格仅明确查记录才 true — 与「可能有用就拉」决策不符

### 3. 条件跳过，不用节点内空跑

- **选择**：图条件边 / 路由动态 `prepare_steps`：false 时不进入后两节点
- **理由**：对齐 `skip_knowledge`；避免「正在翻记录」假字幕
- **替代**：`fetch_history` 内见 false 返回 `[]` 但仍执行节点 — 实现更简单但 UX 差；可作防御性二次检查，主路径仍应跳过

### 4. 上游强制 = 跳过第一节点

| 入口 | 行为 |
|------|------|
| `/clinic/stream`、intent conversation/suggest | 跑 `judge_needs_history` |
| intent `target_type=history` | `force_needs_history=true` 或入口直接 `judge_data_requirement` |
| tip 流式 | 不跑门禁；保留硬编码 `data_requirement` → `fetch_history` |
| tip_graph（若仍用） | 不挂门禁，入口保持范围判断 |

- **理由**：history/tip 已认定需要记录，省布尔 LLM、避免误判 false
- **状态**：`needs_history: bool`、`force_needs_history: bool` 独立字段，不进 `data_requirement`

### 5. clinic 流式步进改造

- **选择**：先 `run_one_step_with_thinking(judge_needs_history)`，再按 flag 拼后续线性表（含或不含 scope+fetch），其余向量/画像照旧
- **理由**：现有 `run_linear_steps_with_thinking` 无条件边；与 intent 流式条件拼步一致
- **`clinic_graph`**：entry = `judge_needs_history`；条件边到 scope 或直接到 `search_vectors` /（`skip_knowledge` 时）`fetch_baby_profile`

### 6. 提示与文案

- 新 prompt：只输出 `{"needs_history": true|false}`
- thinking：`judge_needs_history` ← 现「要不要翻」；`judge_data_requirement` ← 「翻多久」；`fetch_history` 仅在拉取时出现

## Risks / Trade-offs

- [需要历史时多一次 LLM] → 用清晰度与可跳过 API 换成本；强制路径可跳过第一节点缓解 tip/history
- [宽松导致多数续聊仍 true] → 接受；闲聊/纯知识仍受益；后续可加启发式
- [路由线性表与 graph 条件边双份逻辑] → 抽小函数「是否继续拉历史」供两边共用，降低漂移
- [旧 state 无 `needs_history`] → 缺省按 true 处理，兼容

## Migration Plan

1. 合入后 clinic 开放问答自动走门禁；history/tip 行为应与现网「总会拉历史」一致
2. 回滚：去掉第一节点与条件边，恢复 `judge_data_requirement` 为入口即可
3. 无需数据迁移或客户端改动

## Open Questions

- tip_graph 是否在本 change 同步改入口注释/边（流式主路径可不改代码）— 建议任务里「若图仍导出则对齐文档与入口，避免误用挂上门禁」
