## Context

段多维 TYPE 仍用本地弱规则短路（「睡」→ create），问句「睡了多久了」进不了 TYPE LLM。SHAPE 另有结束词表 + 小 LLM + `rule_gap(shape)`。缺口箱写入 type/event/shape/time/quantity，Hub 噪音大。EVENT 已有 `feeding_intents` 短说法飞轮与 `/admin/intent-cache`。产品要求：TYPE（含 SHAPE）按维关键字飞轮；冷路径同次 LLM 出 `need_confirm`+`keywords[]`；TIME/QTY 保留规则；缺口仅 TIME/QTY；Hub 可整理类型向量。

约束：中文注释；禁止自动测试；SSE 真流式 + 中文 reasoning；提示词在 `prompts/system.py`；意图飞轮除外置 prompt 飞轮外允许。

## Goals / Non-Goals

**Goals:**

- TYPE 飞轮优先（独立集合）；命中跳过 TYPE LLM。
- 冷：TYPE LLM → `need_confirm` + `keywords[]`；高置信直用并灌库；需确认则确认后灌库。
- SHAPE 并入 TYPE（end/create/start 由 TYPE 结果表达）。
- 停写 type/shape/event 缺口；Hub/API 仅 TIME/QTY 规则缺口。
- 类型向量 admin API + 兄弟仓 Hub 页（对标事件向量）。

**Non-Goals:**

- 恢复整句整包意图缓存免确认。
- TIME/QTY 去掉规则或建 TIME/QTY 向量飞轮。
- 本仓实现 Go Hub 前端（tasks 标明兄弟仓）。
- 自动把缺口转成类型关键字。

## Decisions

### D1：TYPE 判定顺序

```
句级 target_type（分句）若有 → 服从句级
否则 → 类型关键字库匹配（阈值对齐事件 0.72，可共用常量）
命中 → 采用 payload（target_type/op/history_mode）
未命中 → TYPE 小 LLM（不再跑喂养弱线索 create 短路）
```

保留极薄安全规则可选：`exit` 整句、显式 delete/update 词——若保留须在 design 实现时标为「强线索」；**默认删除「睡/吃」类喂养弱线索 create 短路**。结束语义由 TYPE LLM 或类型飞轮 payload 的 `op=end` 表达，不再依赖独立 SHAPE LLM。

**Alternatives：** 只加「多久」进 history 词表——否决（治标）；全维零规则——否决（TIME grounding）。

### D2：集合与载荷

- 新 Chroma 集合：`feeding_type_cues`（名可微调，禁止与 `feeding_intents` 混存）。
- document = 短关键字（如「多久了」「睡醒」）；metadata/payload：`target_type`、`op`、`history_mode`（及必要 action 语义）。
- MUST NOT 存整包 multi-events；MUST NOT 用复合整句当唯一 document。

### D3：TYPE LLM 契约

同一次调用输出 JSON：

- `target_type` / `op` / `history_mode`
- `need_confirm`（bool）
- `keywords`（string[]，段内可复用的短线索）

提示词约束：问时长/查史口语偏 history+read；记录/睡着偏 create；醒了/睡醒偏 end；不确定才 `need_confirm=true`。SSE `stream(thinking_enabled=True)`。

写入时机：`need_confirm=false` 采用后立即按 keywords 写入；`true` 则用户确认后再写。空 keywords 时可回退段原文规范化短句一条（仍禁止复合整句）。

### D4：与直执行关系

- 热路径飞轮齐 + 无阻塞 → 直执行（与 skip-leaf-confirm 一致）。
- 冷路径仅当 TYPE LLM `need_confirm=true` 才问类型确认；高置信不因 match_source=llm 强制确认。
- 父消歧 / 缺量仍阻塞。

### D5：缺口箱收窄

| dimension | 写入缺口？ |
|-----------|------------|
| time | 是：规则 miss/半命中且调用 TIME LLM（宜要求有 llm_result） |
| quantity | 是：有量线索规则抽空且调用 QTY LLM；**缺量追问可不写或单独 reason 且 Hub 默认过滤** |
| type/shape/event | **否** |

Admin 列表默认 `dimension in (time, quantity)`；存量杂音可清 JSONL 或 Hub 只读新策略。

### D6：Admin API

镜像 `/v1/admin/intent-cache`：

- `GET /v1/admin/type-cache`
- `POST /v1/admin/type-cache/bulk`（同 document 跳过）
- `POST /v1/admin/type-cache/dedupe`
- `DELETE /v1/admin/type-cache/{id}`

Go Hub：新页或并列 Tab「类型向量」，反代上述 API。

### D7：删除独立 SHAPE 路径

- 移除或掏空 `llm_resolve_shape` 主路径调用与 shape 缺口。
- `matches_end_cue` 可作为 TYPE 飞轮种子/提示示例，不再单独短路整段 TYPE（若与飞轮冲突，飞轮/LLM 优先）。

## Risks / Trade-offs

- [TYPE LLM 误标 need_confirm=false] → 提示词示例；Hub 可删错关键字；回执可纠错  
- [keywords 过宽串台] → 约束短线索、禁止整句；阈值 0.72；Hub dedupe  
- [冷启动每句 TYPE LLM] → 可接受；种子灌「多久了/睡着了/睡醒」  
- [Hub 存量缺口脏数据] → 清文件或 filter  
- [与 skip-leaf-confirm 叠层] → 仅 TYPE need_confirm 与阻塞确认  

## Migration Plan

1. 上线类型集合 + store + TYPE 路径改造 + 停写 type/shape/event 缺口。  
2. Admin API；Go Hub 类型页 + 缺口 filter。  
3. 可选：清空旧 rule_gaps.jsonl 或脚本只保留 time/quantity。  
4. 手工验收：「睡了多久了」history；「睡着了」create；「睡醒了」end；Hub 缺口无 type/event。

## Open Questions

- 缺量追问是否完全不写缺口：默认不写（Hub 只要「规则+LLM」类）。
- 类型匹配阈值是否与 EVENT 同 0.72：默认同。
