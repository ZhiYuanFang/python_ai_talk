# 意图段多维与事件短说法

## 管道

- 单事件：零 LLM，段级 TYPE→EVENT→SHAPE→QTY→TIME
- 复合句：LLM 仅分句 → 逐段多维 → 拼装 → 确认（策略 C）→ 落库/查史
- 失败：引导重说，无一次结构化回退

## 事件库发版

1. `CLEAR_FEEDING_INTENTS_ON_STARTUP=true` 启动一次清空 `feeding_intents`
2. 改回 `false`
3. 运行 `python scripts/seed_event_phrases_from_dict.py`（或 Hub `POST /v1/admin/intent-cache/bulk`）
4. bulk payload：`{ "document": "尿尿了", "payload": { "event_id": "...", "event_name": "尿尿", "kind": "leaf" } }`

## 规则缺口

- 写入：非事件维 miss / 事件 miss → `data/rule_gaps/gaps.jsonl`（相对 chroma 目录旁）
- API：`GET /v1/admin/rule-gaps`、`PATCH /v1/admin/rule-gaps/{id}`（body `{"status":"dismissed"}`）
- Go Hub 页：兄弟仓二期代理本 API；人工改 Python 规则后发版，非热更新
