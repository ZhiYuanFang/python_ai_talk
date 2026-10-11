## Context

整句缓存飞轮已废；段多维 + 维级小 LLM 负责对齐。`drafts_to_intent` 仍 `need_confirm=True`，`intent_pipeline` 在 `need_confirm or match_source==llm` 时建 `leaf_confirm`。产品要求：无阻塞时直落库/直查史。

## Goals / Non-Goals

**Goals:**

- 完整叶子意图无二次 yes/no。
- 阻塞澄清保留。
- 短说法挂执行成功。

**Non-Goals:**

- 恢复整句整包免确认回放。
- 取消父消歧/缺量/多叶消歧。
- 改 Go batch 契约。

## Decisions

### D1：何时直执行

同时满足：

1. `target_type` 为 feeding 或 history（exit/conversation/失败重说除外）。
2. 每个 events[] 项有非空 `event_id`（或 history 允许的父 id 已按现规展开/确认——若仍是 create 父则走消歧，不直执行）。
3. 无 `missing_quantity`。
4. 无消歧 pending 需求（父 create、备注多叶等已在段循环提前返回的保持原样）。
5. `segment_failed` 为假。

→ `need_confirm=false`，管线直接 `_execute_after_confirm`（或图内已有 cud/speak 边）。

### D2：废除 llm 强制确认

删除或改为：仅当显式 `need_confirm` 或存在阻塞字段时确认。EVENT/SHAPE 小 LLM 命中不再单独强制 `leaf_confirm`。

### D3：多段

无阻塞且同质多段：一次 batch 执行全部（策略 C 的「拼问」改为「拼执行」）；混 op 仍可按现有路由（cud vs read）拆，但不对用户拼 yes/no。

### D4：短说法写入

在 execute_history_crud / speak_history（或管线执行成功回执后）对已成功段调用 `add_event_phrase`；失败段不写。

### D5：查史

history 且事件已定、无消歧：直 `speak_history`，不再「请确认是否查询…」（与 feeding 直执行对称）。若产品仍要查史软确认，可仅对 history 保留——**默认与 feeding 一样直执行**。

## Risks / Trade-offs

- [LLM 偶发错直接落库] → 回执文案清晰；后续可加撤销；规则缺口继续记  
- [用户失去纠错点] → 阻塞澄清仍在；错误可用下一句修正  
- [查史也直出] → 与「少问」一致；若嫌吵可再收窄  

## Migration Plan

1. 改 need_confirm 与 pipeline 门控。  
2. 短语写入挪到执行成功。  
3. 验收：睡醒了直结束；缺量仍追问；父消歧仍问。  

## Open Questions

- 查史是否与 create 一样免软确认：默认是。
