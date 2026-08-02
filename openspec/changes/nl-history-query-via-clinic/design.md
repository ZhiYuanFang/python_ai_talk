## Context

Intent 入口先 `match_event_by_vector`：含事件名的查询句易高置信打成 feeding。分类虽有 history，但图上 history 走独立短链 + `history_answer`，与产品「调 clinic」不一致。方案 A：history → `call_clinic_agent`；纯查记录跳过 `search_vectors`。

## Goals / Non-Goals

**Goals:**

- 查询句不误记 feeding
- history 统一 clinic agent + 查记录答题质量
- `target_type=history` 时跳过知识向量检索
- 支持「分别」多事件上次时间

**Non-Goals:**

- 不删除 `TargetType.HISTORY` / `generate_response` 文件（可摘边；文件可留）
- 不强制 clinic HTTP 直连一律 skip 知识（仅 intent history 必跳；HTTP 可选后续）
- 本 change 不强制跳过 `fetch_baby_profile`（可保留）
- 不做新 HTTP 接口

## Decisions

### 1. 查询句向量门禁（规则，先于/内置于 match）

- **选择**：对用户文本做轻量正则/关键词（何时、什么时候、上次、上一次、最近一次、分别、多少次、多少毫升等）；命中则 **不** 返回向量 feeding 结果，直接 `match_source=llm` 降级分类
- **理由**：不依赖阈值，专治「拉屎+什么时候」
- **备选**：只用 LLM → 贵且仍可能被向量短路

### 2. history → call_clinic_agent

- **选择**：`route_after_classify` 中 history 与 conversation/suggest 一样走 `call_clinic_agent`；intent stream 步进同步
- **理由**：产品 A；共享会话/飞轮/闺蜜生成
- **备选**：保留 history 短链 → 拒绝

### 3. skip_knowledge 条件边

- **选择**：state 设 `skip_knowledge=True`（由 call_clinic_agent 在 history 时写入）；`clinic_graph` 在 `fetch_history` 后条件：skip → `fetch_baby_profile`，否则 → `search_vectors`
- **理由**：图语义清晰；search_vectors no-op 仍会多一步 thinking
- **clinic 路由步进**：若有线性步骤表，history 场景步骤不含 search_vectors（与 flag 一致）

### 4. clinic_answer 查记录模式

- **选择**：system/user 增加规则：若问题是查上次/何时/分别，必须以喂养记录为准答出时间；多事件分别作答；无记录老实说；此类题不受「约 50 字」硬限制（可略长）
- **理由**：现闺蜜短答与事实查询冲突

### 5. 历史字段裁剪

- **选择**：注入 prompt 前只保留 eventName、eventNumber、startTime、endTime、remark（缺则省略）；clinic_answer / 相关 history 注入共用小函数
- **理由**：降噪、省 token；查时间题尤其需要

### 6. data_requirement 提示

- **选择**：补充「上一次 X」→ 对应 event_ids + 足够 time_range；「X 和 Y 分别」→ 多个 ids；limit 足够覆盖各取最近一条

## Risks / Trade-offs

- [门禁误伤「刚才拉屎了什么时候记的」类边角] → 宁可进 history/clinic 也不误落库；可后调词表
- [history 进 clinic 变重] → skip vectors 已缓解；画像可后续再跳
- [图与路由步进不一致] → 改图时同步 clinic/tip/intent 步进表

## Migration Plan

1. 部署后验：「上一次拉屎是什么时候」非 feeding、有时间答案；「分别」两时间；「拉屎了」仍可 feeding
2. 回滚：恢复 history 短链路由 + 去掉门禁/skip

## Open Questions

- 无（A + skip vectors 已确认）
