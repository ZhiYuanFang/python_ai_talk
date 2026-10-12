## Context

线上句「下一次喂养是什么时候」首次即被 `infer_expected_history_mode`（「什么时候」→ point）在 `resolve_type` 中强制为 `read+record`，再走 `speak_history`，答成「上一次…」。读路径仍跑备注 LLM；数量线索正则对「下一次」中「一」假阳性进 QTY LLM。探索已定：A+B 同 change；删定轨害人规则、保留有效规则；数量规则→飞轮→LLM；备注整段飞轮；read 跳过备注/数量。

约束：中文注释；禁止测试文件；feeding 内改；时间仍无飞轮。

## Goals / Non-Goals

**Goals:**

- 定轨：`record|predict` 仅由 OP/source/predict 飞轮与 OP LLM 判定，不被查史词表短路。
- 保留 exit/delete/end 与「record 已定后的 history_mode / 缓存冲突」用途。
- 数量：规则 → 飞轮补缺 → 真线索 LLM → 整段回写；收紧线索。
- 备注：整段飞轮（含空串）；read 不跑备注/数量。
- OP 提示词覆盖「下一次…什么时候」→ predict+next。

**Non-Goals:**

- 删除全部本地规则（exit/delete/end 保留）。
- 自动清空错污染 chroma（运维/Hub 手动）。
- 时间向量飞轮；整句「意图结果」总缓存（可后续）。
- Hub 前端（可选兄弟仓任务）。

## Decisions

### D1：删除定轨短路，不删 infer 函数

从 `resolve_type` **移除**：

1. 块「查史强线索 → 直接 return read+record」；
2. 「OP 飞轮 hit read 且 source 未命中时，因 `infer_expected_history_mode` 有值而填 record」。

保留：

- exit / delete / 睡醒→end；
- **仅当** `read_source` 已为 `record`（飞轮或 LLM）后，用 `infer_expected_history_mode(text) or "point"` 填 `history_mode`；
- `history_mode_cache_conflict` 等缓存门闩。

**Alternatives：** 仅去掉「什么时候」保留「上次」本地拍 record — 否决（用户要求避免本地定轨错判，统一走飞轮/LLM）。

### D2：resolve_type 目标序

```
显式 CUD/exit 规则
  → OP 整段飞轮
  → read 时：source 飞轮 → predict 则 predict 飞轮/维 LLM
  → OP 小 LLM（定轨 + 缺维）→ 拆写 OP/source/predict
```

### D3：数量维顺序

```
① extract_quantity_from_text（规则）
② 规则 null → qty 整段飞轮
③ 仍 null 且 has_quantity_clue（收紧后）→ QTY LLM → 回写
④ 无线索 / number 缺量追问 → 不写飞轮
```

收紧 `_QTY_CLUE_RE`：中文数字必须贴「毫升|ml」或落在「吃了/喝了/喂了」后，禁止裸匹配「一」。

### D4：备注整段飞轮

- Collection 如 `feeding_remark_cues`；document=段整句；payload=`remark`（允许 `""` 表示已确认无明细）。
- 顺序：已有别名/反查 remark 可跳过 LLM；否则飞轮 → 明细 LLM → 回写。
- **`target_type=read` 时整维跳过**（含 predict）。

### D5：OP 提示词

在 `SEGMENT_TYPE_LLM_PROMPT` 语义纠偏中增加：  
「下一次喂养/下次什么时候喂」→ `read` + `read_source=predict` + `next` + clock|remain；  
并明确：**不得**仅因「什么时候」判为 record。

## Risks / Trade-offs

- [查史「上次」冷启动多打 OP LLM] → 整段飞轮回写后热路径恢复；接受短期成本
- [空 remark 飞轮膨胀] → 仅 C/U 且事件已定才写；可 Hub 清理
- [旧污染 speak/OP 条目] → 用户手动清；提示勿把 predict 句写入 speak

## Migration Plan

1. 发版删定轨短路 + qty/remark 飞轮 + 提示词。
2. 手工清已知错 document（下一次喂养是什么时候 的 speak/record 污染）。
3. 金线：「下一次喂养是什么时候」→ predict；同句二次无备注/数量 LLM；「吃了差不多一百二」qty 二次可跳 LLM。
4. 回滚：恢复查史短路（应急，不推荐）。

## Open Questions

（无：删定轨短路与保留有效规则已拍板。）
