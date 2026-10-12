## Context

现状：`target_type`∈{feeding,history,predict,conversation,exit} 兼路由与时态；TYPE 短关键词飞轮易把「多久」串台；写库走 Go `event/batch`；TIME/QTY 规则+LLM+rule_gap；另有 history_speak / type / intents 多套集合。

产品重梳理：顶层按 **对数据的动作** 分轨；问答（含预测）收进 R；飞轮 document=整段；时间不做飞轮；数量做飞轮；一期 Python 分轨、底层仍 batch。

## Goals / Non-Goals

**Goals:**

- 顶层 `create|read|update|delete|exit|other`；段级串行；统一汇总。
- U·end 定位进行中；无则转 C（按 one/number/time；time 无闭合追问）。
- R 内 record|predict + 播报维；沿用 active-eta / imminent。
- 分层整段飞轮；热路径可跳过对应 LLM。
- 时间：仅规则+TIME LLM+rule_gap。
- 数量：规则可选 + QTY LLM + qty 飞轮。
- 一期写库仍 `batch_history_events`。

**Non-Goals:**

- 一期拆 Go create/update/delete 独立 HTTP（二期）。
- 时间向量飞轮。
- 恢复 conversation 闲聊主轨。
- 飞轮 document 使用短关键词（明确禁止为主策略）。
- 本仓实现 Go Hub 前端（tasks 标兄弟仓）。

## Decisions

### D1：顶层枚举与对外字段

对外/内部主轨字段建议统一为 `op_rail` 或复用 `target_type` 取值改为 CRUD 语义（实现择一，须全仓一致）：

| 值 | 含义 |
|----|------|
| create | C |
| read | R |
| update | U |
| delete | D |
| exit | 退出 |
| other | 暂不支持，会话可续 |

废除主轨：`feeding`/`history`/`predict`/`conversation`/`suggest`。  
旧 `IntentOp` 与 batch 项内 `op` 仍可在写入映射层使用（create/end/update/delete/read）。

**Alternatives：** 保留 feeding+op — 否决（type 仍糊）。

### D2：段循环与统一汇总

```
split → for each segment:
  classify OP → run rail → SegmentOutcome{ok|clarify|other|error, message}
→ join messages（A 结果 / B 需补充 / C 结果）
```

单段 clarify 不中断后续段；整轮一次回复。

### D3：U·end → 无 open → C

1. 定事件 + 时间窗 → filter 史  
2. 找仅 start、无有效 end  
3. 有 → batch update（补 end）  
4. 无 → 转入 C 全流程：定事件 type  
   - one → create+one  
   - number → create+number（缺量追问）  
   - time → 须闭合 start+end；否则 clarify  

### D4：R 内部分维

- `source`: record | predict（整段飞轮）  
- record: 时段（规则，非飞轮）→ list → speak point|span（整段飞轮；可含 point_pick/open_speak）  
- predict: channel active|next + time_answer clock|remain（整段飞轮）→ ETA/imminent → 模板  

### D5：飞轮分层（document=段整句）

| 层 | Collection（名可微调） | payload |
|----|------------------------|---------|
| OP | feeding_op_cues | op_rail |
| 事件 | feeding_intents（演进） | event_id/name |
| 数量 | feeding_qty_cues | quantity |
| R·source | feeding_read_source_cues | record\|predict |
| R·record 播报 | feeding_read_speak_cues（或演进 history_speak） | speak + 选行策略 |
| R·predict | feeding_predict_cues | channel + time_answer |
| U/D 定位 | feeding_locate_cues | 策略码（不存 historyId） |

阈值从严；命中失败则该层 LLM；成功回写整段。  
**禁止**时间飞轮。短关键词 TYPE/history_speak 种子迁移或清空。

### D6：时间 vs 数量

- TIME：规则 → LLM → rule_gap；无飞轮。  
- QTY：规则可先；LLM 快 → qty 飞轮；无线索追问不写飞轮；rule_gap 可选保留。

### D7：一期 batch 映射

分轨产出规范化 events 项后，仍调用 `batch_history_events`。映射表在实现时锁定（create/update/delete/end→batch op/action）。二期再拆 API。

### D8：一期落地顺序建议

1. 枚举 + OP 分类/飞轮 + other/exit + 段汇总骨架  
2. C 轨（事件+时间规则+量飞轮）接 batch  
3. R 轨（source+播报+predict）  
4. U/D（定位+end→C）  
5. 清理旧 TYPE 短词飞轮 / admin  

## Risks / Trade-offs

- [整段飞轮冷启动] → 冷路径回写 + Hub bulk 整句种子  
- [同义句难命中] → 接受再 LLM；禁止退回短关键词  
- [TIME LLM 仍慢] → 靠规则覆盖与缺口人工；不矢量化偷快  
- [batch 与分轨语义漂移] → 单测级手工验收矩阵；映射表写死在 design/代码注释  
- [多段部分成功] → 产品接受统一汇报；澄清下轮只补缺口段  

## Migration Plan

1. 发版新枚举与 OP 飞轮；兼容读旧 type 一版（可选短窗）或硬切。  
2. 清空/停用短关键词 type_cues 热路径。  
3. 灌整句种子（多久了/睡着了/睡醒了/还有多久醒来…）。  
4. 验收金线后关兼容。  
5. 回滚：恢复旧 TargetType 路由（应急）。

## Open Questions

（探索已定：一期仍 batch；时间无飞轮；数量有飞轮；end→U→无则 C。实现期仅细化 batch 字段映射表。）
