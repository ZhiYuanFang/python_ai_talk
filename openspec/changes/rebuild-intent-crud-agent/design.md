## Context

当前意图链是「事件名快路径 + Go 二次落地」：

- `match_event_by_vector` 对整句 `n_results=1`，高置信直接 `feeding` 并 END；飞轮把确认原话写入 `feeding_events` 并绑到 **一个** `event_id`。复合句会被压成单事件。
- LLM 已有 `action=multi` + `events[]`，但确认 pending 只挂 `events[0]`，飞轮仍写单叶子。
- Go `mapPythonIntentToLandPlan` / `handleMultiEventIntent` 再用原文匹配、`pendingChild` 消歧、`AddHistory`。多事件路径忽略子项 `event_id`、数量写死 1。
- Python `http_client` 只能读历史；非流式 `/intent` 被改成 `call_clinic_agent`。
- 查记录：`fetch_history` 用 `today|yesterday|last_7_days` 映射（「今天」窗有误）；无 `eventIds` 时拉全类型；点查不按备注检索。分类提示对字典外词设 `is_new_event=true`。
- `GET /device/history/api/filter` 只有 `eventIds / startTime / endTime / limit`。`history.remark` 可空，**不是索引键**。`LIKE '%AD%'` 无法走 remark 单列 B-Tree 前缀。

约束：Python 为智能内核，经 HTTP 调兄弟仓，不直连 DB；`feeding` 不得导入 `clinic`；代码中文注释；不写测试文件。Go 改动在 `d:\work\go_ai_talk`。

## Goals / Non-Goals

**Goals:**

- 删除单事件飞轮代码与整份 `feeding_events` 事件名向量（匹配节点 + 存储 + 字典同步）；意图缓存加速重复 CRUD（含 multi 与备注关键词）。
- Python 确认后 **一次** 批量 HTTP 落库；回执说明成功/失败原因。
- 查记录先定事件（或日汇总压缩）；点查带备注；字典外词（如 AD）经备注探针定为已知事件后确认再查。
- Go 语音只透传；filter 支持备注模糊；提供可复制 DDL。
- `/intent` 与 `/intent/stream` 同图；新增 `/v1/clinic`。

**Non-Goals:**

- 不在意图路径创建新事件类型（不做 `is_new_event` 建档）。
- 不把 clinic `companion_session` 当意图对话账本。
- 不删知识库向量（`mother_baby_knowledge` / Q&A `source=user`）。
- 不删意图缓存 Collection `feeding_intents`。
- 不在本变更做 Flutter 实现。
- 不生成测试文件。
- 不为 `LIKE '%x%'` 假装单列 B-Tree 能加速；索引策略见决策 10。

## Decisions

### 1. 拆除事件名向量（方案 B，不是只摘节点）

- **选择**：意图匹配单位只剩意图缓存。删除 `match_event_by_vector`、`EventVectorStore`、Chroma `feeding_events`，以及启动 / `event_cache` / `scripts/build_vector_db.py` 对标准事件向量的初始化与同步。
- **同时删除**：`add_user_expression`、用户表达的 `increment_*` / `check_and_cleanup`、`apply_flywheel_after_leaf_resolution` 飞轮写入（该 Collection 已不存在，写入无意义）。
- **不删**：知识库 `source=user`（Q&A / care-alert 飞轮）；`feeding_intents`。
- **备选否决**：只从图拿掉匹配、保留 `feeding_events` 空转同步 — 仍占磁盘与启动时间，且容易被重新接回快路径。
- **备选否决**：保留标准事件名向量作冷启动身份 — 单位仍是单个 `event_id`，复合句/查改删仍会被 Top-1 吞掉；分类提示已含完整事件字典，不需要第二套向量身份。

### 2. 意图缓存飞轮

- **Collection**：如 `feeding_intents`。document = **改写后的独立问答句**（clinic 风格，不是「嗯/是的」）。
- **metadata**：`{op, events[]}`，查记录可含 `remark_keyword`。**禁止**缓存 `history_id`。
- **写入时机**：用户确认（或高置信单次 create 免确认）**且**批量接口至少一条成功。
- **命中**：高相似则作为分类结果；改/删命中后现查 latest/filter 再执行。
- **备选否决**：继续往 `feeding_events` 写用户表达 — 与标准向量混空间，复合句仍丢件。

### 3. 会话连续性（如何判断首轮）

当下与本变更均 **没有** 意图轮次账本。

| 信号 | 含义 |
|------|------|
| 无 `conversation_id` | 首轮 / 新对话 |
| 有 cid 但 `clarification_store` 无 pending | 新一轮独立意图（可命中缓存） |
| 有 cid 且有 pending | 连续对话：硬匹配「是的/1/取消」或澄清 LLM |

clinic `companion_session` **不得**用于意图 CRUD。本变更不新做意图 turn log；改写缓存句只在「确认成功后」用本轮用户原话 + 结构化结果生成独立句，不依赖历史多轮原文。

### 4. 意图图拓扑

```
START → match_intent_cache
          ├─ 命中 CRUD →（改/删现查 id）→ execute_history_crud（batch）→ 模板 content → END
          └─ miss → [可选] remark_probe（点查句式 + 字典外词）
                       → classify_intent（可见探针一行摘要）
                            ├─ 需确认 → END（pending，不写库、不写缓存）
                            ├─ create/update/delete 已确认或免确认 → batch → 模板 → 写缓存 → END
                            ├─ read 已定事件 → fetch_history（eventIds+unix+可选 remark）→ 模板 content → END
                            ├─ conversation / exit → END
                            └─ 不再出现 suggest / call_clinic_agent / 历史答题 LLM / match_event_by_vector
```

图上 **MUST NOT** 注册 `match_event_by_vector`。缓存 miss 后唯一语义入口是分类（探针只注入一行备注摘要，不调 LLM）。

### 5. 何时调 LLM（意图路径）

| 调用 | 何时 |
|------|------|
| A 改写独立句 | 仅确认且至少一条落库成功后写缓存时（一次，非每轮） |
| B 分类 | 意图缓存未命中（含首次「喝了奶粉」；不再有事件名向量快路径） |
| C 澄清 | 有 pending 且用户自由文本，硬匹配未命中 |
| 备注探针 | **不调 LLM**（Go filter） |
| 查记录播报 | **不调 LLM**（模板） |
| `judge_data_requirement` | **删除**（分类直接给 unix + event_ids） |
| `call_clinic_agent` | **从意图删除** |

稳态：未见过的 CRUD = 1 次分类 + 确认；缓存命中 = 0；澄清自由文本 = +1。`/v1/clinic` 仍有陪伴侧隐式反馈 / 改写 / 生成。

硬匹配「是的。」「1」「取消」：**不**走澄清 LLM。

### 6. 确认 vs 落库

- 缓存 miss → 分类 LLM → 默认 `need_confirm`，**本轮不落库**（`create_leaf_confirm_pending`）。
- 多事件一律软确认。
- 父节点只消歧，永不落库。
- 字典外名称记事件：`missing_events` + 文案，不建类型、不写 history。
- **免确认**：仅 **意图缓存高置信命中**（该独立句曾确认并至少一条落库成功）。分类 LLM 结果默认 `need_confirm`。
- 确认后走 batch；未确认不写缓存。

### 7. Go 批量 CRUD（一条 HTTP）

- **选择**：新增 `POST /device/history/api/event/batch`，`items[]` 每项 `op` 为 `create|update|delete|end`（create 再带 `action=start|end|one`）。
- 部分成功：做成的做，失败项带原因；Python **一次** HTTP，不 N 次 add/update/delete。
- 既有单条 add/update/delete/end-latest/latest **保留**给 App；语音/意图只用 batch。
- Python `http_client` 封装 batch；`end` 对应 end-latest 语义。

### 8. 落库回执模板

`content` 必须让用户感知结果，禁止静默成功。

- 全成功：逐项「已记录/已改/已删 + 事件名 + 用量/时间」。
- 部分成功：同一段同时列出成功项与「X 未入库，因为 …」（缺叶子、接口失败、无最新行等）。
- 全失败：只说明原因，不假装已记。
- **不**用生成 LLM 编回执。

### 9. 查记录：先定事件，两种模式

分类（或缓存）给出：`op=read`、`event_ids`、`startTime`/`endTime` Unix 秒。提示词注入「现在」上海时区 + unix；Python 只校验/夹紧。

**删除** `fetch_history` 的 `today|yesterday|last_7_days|…` 映射。clinic `judge_data_requirement`、tip、care-alert 拉史改为传入 **已算好的 unix**，不得再传枚举。

| 模式 | 何时 | 拉什么 | 进 prompt / 播报 |
|------|------|--------|------------------|
| 点查 | 何时发生了什么 | **必须** `event_ids`；可加 `remark` | 每条：时间 + 用量 + **备注**；模板播报，不进生成 LLM |
| 日汇总 | 整天 / 定不了事件 | 可拉窗口内多类型，**立刻**压成 `{事件名}+{备注}：用量/时长/次数` | **禁止**原始 list 进 prompt |

空 `event_ids` 的点查 **MUST NOT** 把全类型原始行塞进 prompt。多事件点查：每事件一行或「没有记到 X」。

### 10. 备注模糊 + AD：探针让分类「看见」已知事件

**问题**：用户说「上一次何时吃的 AD」。字典无 AD；AD 在营养品 `remark` 里。不能靠模型常识认亲，也不能为找 AD 拉全量原始史进 prompt。

**Go filter**（原接口加字段，不新开路径）：

| 字段 | 规则 |
|------|------|
| `remark` | 非空则 `remark LIKE %keyword%`（先转义 `%` `_`）；与 `eventIds` **AND** |
| 空 `eventIds` + 有 `remark` | 仅作 **探针**：强制 `limit≤20`，建议带时间窗（默认近 90 天） |
| 正式点查 | **必须**带 `eventIds` + 可选 `remark` + unix 窗 |

`remark` 列 **保持可空**：NULL 与空串 = 无备注，模糊条件 **排除** 这些行（`remark IS NOT NULL AND remark <> ''`）。不得 `ALTER` 成 `NOT NULL`。

**索引（可复制 SQL）**：`docs/migrations/history_remark_filter_index.sql`（兄弟仓）。

- `LIKE '%AD%'` **不能**靠 `remark` 单列 B-Tree 前缀加速。
- 正式/探针都先用 `(device_no, start_time)` / `(device_no, event_id, start_time)` 收窄，再扫备注（探针 limit 很小）。
- 另加 `FULLTEXT ... WITH PARSER ngram` 供后续 `MATCH AGAINST`；本期 Go 可用收窄后的 `LIKE`。空/NULL 不进 FULLTEXT，符合可空语义。
- 运维手工执行 SQL；代码不自动迁库。

**定事件流程（不把原始行塞进分类）**：

```
点查句式 + 剩余词不在字典
    → Go 探针 remark≈词，limit 5～10
    → 只注入一行摘要：「备注含 AD：营养品 ×3，最近昨天 20:10」
    → 分类输出 event_ids=[营养品] + remark_keyword=AD + need_confirm
    → 「没有叫 AD 的事件。是要查上一次吃的营养品吗？（按备注 AD）」
    → 确认后正式 filter：eventIds + remark + unix
    → 模板播最近一条（含备注）
```

| 探针 | 行为 |
|------|------|
| 唯一事件 | 确认该字典真名 |
| 多事件抢同一备注 | 「AD 出现在营养品和药品，查哪个？」 |
| 0 命中 | 分类可用常识猜候选，仍禁止新事件；确认后正式查，没有则「最近没有备注里带 AD 的 …」 |

光说「AD」（无上次/何时）：先问记录一笔还是查询上一次。

分类硬规则：字典外专名优先当备注；**禁止** `is_new_event` 建档。

缓存：确认并成功播报后写 `op=read` + `event_ids` + `remark_keyword`，不得缓存「事件=AD」。

### 11. Python 落库，Go 管道

Go `applyUnifiedIntentResult` 收成：

- `NeedConfirm` → 存 cid，播 `confirm_message`
- 否则播 `content`（空则固定技术兜底，不按 action 编话术）
- `target_type=exit` → 结束会话
- **删除** land plan、`handleUnifiedIntentAction` 写库、`handleMultiEventIntent`、`pendingChild`、preamble 短路

### 12. 响应契约（兼容期双轴）

`IntentResponse` 增加：

- `op`: `create | read | update | delete`（空 = conversation/exit）
- `events[]` 子项可选 `history_id`（本轮结果，**不是**飞轮字段）
- `remark_keyword`（查记录可选）
- `missing_events`（字典外、未落库的名称）

`action` 保留：`start|end|one|multi|search|reply|exit`。`multi` ≡ `op=create` 且 `len(events)>1`。

### 13. HTTP 原子性

| 路径 | 语义 |
|------|------|
| `POST /v1/analyze/intent` | 与 stream **同一**图 / 后处理 |
| `POST /v1/analyze/intent/stream` | 同上 + SSE thinking |
| `POST /v1/clinic` | **新建**，`ClinicRequest`，`{answer, answer_id}` |
| `POST /v1/clinic/stream` | 不变 |
| `POST /device/history/api/event/batch` | **新建**，意图/语音专用 |
| `GET /device/history/api/filter` | 增加 `remark` |

作废：非流式 `/intent` → clinic。前端陪伴迁 `/v1/clinic`。Go 成长建议改 clinic 非流式。

### 14. 模块边界

- CRUD、意图缓存、history 读写：`feeding` + `shared.http_client` + `shared.fetch_history`
- 陪伴：仅 `clinic` 路由进 `clinic_graph`
- 删除 `app/feeding/graphs/nodes/call_clinic_agent.py`

## Risks / Trade-offs

- **[存量 feeding_events]** → 代码不再创建/查询该 Collection；磁盘残留可运维手动删 Chroma 目录中对应集合，不影响知识库。
- **[首次 CRUD 必走 LLM]** → 可接受；第二次同类独立句走意图缓存。
- **[改/删改错行]** → 不缓存 id；模糊时确认；无 latest 则文案说明，不写库。
- **[TTS 与前端]** → `/intent` 恢复喂养后，仍打该 URL 的陪伴客户端会得到短闲聊。必须迁 `/v1/clinic`。
- **[双写窗口]** → Go 先下线 voice `AddHistory`，再开 Python batch，或同版本发。
- **[LIKE '%x%' 全表扫]** → 探针强制 limit + 时间窗 + device 复合索引；正式点查必须带 event_id。
- **[FULLTEXT ngram 未装]** → SQL 文件分步，复合索引可单独执行；Go 本期用 LIKE。
- **[探针 0 命中]** → 确认猜候选，不建新事件。
- **[内存 pending 重启丢失]** → 与现网一致；用户再说一遍即可。

## Migration Plan

1. 运维在 history 库执行 `docs/migrations/history_remark_filter_index.sql`（可先只跑复合索引）。
2. Go：filter `remark`、batch 接口、语音透传、成长建议改 clinic。
3. Python：删单事件飞轮与 `feeding_events`、意图缓存、同图 `/intent`、`/v1/clinic`、模板回执、探针 + 分类规则、unix 拉史对齐。
4. 前端：陪伴改 `/v1/clinic`。
5. 回滚：恢复 Go 写库与旧 `/intent`→clinic 会重新引入双语义，只作紧急开关。

## Open Questions

- 意图缓存相似度阈值（可先复用现网高/中置信，实现时标定）。
- Flutter 是否与本 Python/Go 同一迭代交付。
- FULLTEXT ngram 是否在目标 MySQL 已启用（未启用则只执行复合索引）。
