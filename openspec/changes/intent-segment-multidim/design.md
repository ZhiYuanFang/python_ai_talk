## Context

当前意图图主路径为：`match_intent_cache`（整句 embedding → 整包 `events[]`，`need_confirm=False`）→ `overlay_slots` → 执行/查史；未命中则 `classify_intent` 一次吐满血 JSON（整表事件 + 多 events）。父消歧与多事件确认在图外 `intent_pipeline`。整句近邻导致复合句串台与叶子误继承；满血分类提示重、易幻觉。

约束：业务注释中文；禁止自动写测试；feeding 不直接引 clinic；SSE 路径 LLM 须真流式 + 中文 reasoning；意图缓存飞轮除外置 prompt 飞轮外可保留，但形状须改为事件短说法。

交付：**先 Python 行为闭环，再 Go Hub 缺口页。**

## Goals / Non-Goals

**Goals:**

- 单事件零 LLM 多维拼装；复合句 LLM 仅分句后段循环多维。
- 删除一次结构化与整包意图免确认主路径。
- 事件维向量飞轮（0.72）；发版清空 `feeding_intents` 并短说法种子重建。
- 非事件维规则 miss → 缺口收件箱 + admin API；Hub UI 二期。
- 确认 C；number 缺量追问；失败引导重说。

**Non-Goals:**

- TYPE/TIME/QTY 自动向量飞轮（本变更不建）。
- 从 Hub 热更新 Python 规则代码。
- 保留双轨「旧 classify 保底」。
- 本仓实现 Go Hub 前端（tasks 标明兄弟仓；本仓可先提供 API 契约）。

## Decisions

### D1：管道形态

```
单事件？ → 段 = 整句 → 多维
复合？   → LLM 分句(+句级 type) → for 段: TYPE→EVENT→SHAPE→QTY→TIME
失败     → 重说文案，不回退一次结构化
```

单事件判定：便宜信号（无明显并列/多谓语、事件维不宜多命中等）；吃不准当复合。

**Alternatives：** 一律 LLM 分句（更慢）；规则硬拆复合句（易错）——否决。

### D2：多维职责

| 维 | 实现 |
|----|------|
| TYPE | 规则线索 + 小 LLM；句级 type 优先于段 |
| EVENT | 词典 → 向量 0.72 → 小 LLM；库 document=短说法 |
| SHAPE | 由事件 type + op 推导 |
| QTY/TIME | 现有规则；半命中弃权；长尾小 LLM；缺量追问 |

**Alternatives：** 四维都向量——否决（时间 grounding 弱、复杂度高）。

### D3：事件库 vs 旧缓存

- Collection 名可仍为 `feeding_intents`：`reset_collection` + 字典别名种子 + 确认后写短说法。
- payload：**禁止**整包 multi-events 回放；存 `event_id` / `event_name` / `kind`。
- 命中日志：段原文、document、score、event_id。

### D4：确认 C

- 阻塞：create 父消歧、number 缺量追问。
- 其后：段数少且同质（如同为 create 叶子）→ 一次拼问；≥阈值或混 op → 逐段。
- 默认短拼问阈值建议 **≤3**（实现常量，可调）。

### D5：规则缺口收件箱

- Python volume 持久化（JSONL 或轻量文件库，非向量）。
- 写入：TIME 半命中/有词无钟点、TYPE/TIME/QTY 走了 LLM 兜底、number 缺量追问等；短窗按 dimension+segment 去重。
- API：`GET/PATCH /v1/admin/rule-gaps`（列表、标 dismissed）。
- Go Hub：代理 + 列表页（二期）。

### D6：图与代码删除

- 移除或掏空：`match_intent_cache` 整包免确认、`overlay_slots` 作为独立「缓存后覆盖」节点（逻辑并入段 TIME/QTY）、满血 `INTENT_CLASSIFICATION_SYSTEM_TEMPLATE` 主路径。
- 保留：`execute_history_crud` / `speak_history` / clarification pending / parent 消歧服务，改为消费拼装结果。

### D7：分阶段

1. Python：管道 + 事件库 + 缺口 API + 清库种子剧本。  
2. Go：Hub 缺口页。  
Python 未上线前不清生产库；清库与切流量同窗口。

## Risks / Trade-offs

- [分句改写语义] → 约束「保留查史信号/原文子串」；Scenario 覆盖「今天…几次」  
- [单事件误判为复合] → 多打一分句 LLM，可接受；反向误判用复合信号保守  
- [清库后冷启动] → 字典种子必须同步发版  
- [缺口刷屏] → 去重 + 仅 miss/兜底写入  
- [Go 滞后] → Python API 先可用 curl/临时页验收  

## Migration Plan

1. 合并 Python 代码到可切换状态。  
2. `CLEAR_FEEDING_INTENTS_ON_STARTUP=true` 清空 → 灌短说法种子 → 改回 `false`。  
3. 验收串台反例与查史复合句。  
4. Go Hub 接 rule-gaps。  
5. 回滚：困难（行为破坏性）；需旧镜像 + 旧 volume 备份，不承诺自动回迁整包缓存。

## Open Questions

- 短拼问段数阈值是否固定为 3（默认是）。  
- 查史多段是否允许跳过软确认直接播报（默认否，仍走确认 C）。  
- 事件维 miss 是否也写入 rule-gaps（默认 **是**，`dimension=event`，便于补种子）。
