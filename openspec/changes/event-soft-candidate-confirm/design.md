## Context

段多维 EVENT 阶梯末：`llm_resolve_event` + `SEGMENT_EVENT_LLM_PROMPT` 在无把握时强制空 `event_id`，且明示禁止猜「营养品」等类别。`resolve_segment` 在 `ev` 空时 `fail_reason=event_unresolved`，`drafts_to_intent` 产出「无法识别对应的事件…」，`segment_failed` 结束图，**不进** `leaf_confirm` / 消歧。

既有确认壳已具备：`create_leaf_confirm_pending`（单叶是/否）、`create_remark_disambiguation_pending` / parent 消歧（多 options）、确认后 `add_event_phrase` 写短说法。缺口是 EVENT soft 出口与 LLM 契约。

探索拍板：**A**（表内为先 → 软推测 → 问用户）+ **确认后飞轮** + **多候选优先** + **删除「禁止猜营养品」硬空句**（猜改为必须确认，非静默升格）。

## Goals / Non-Goals

**Goals:**

- 梯子未唯一命中时，EVENT LLM 给出表内 `candidates[1..K]`（K≤3）。
- K=1 → 叶子软确认；K≥2 → 多选消歧；K=0 → 无法识别。
- 未确认不执行、不写飞轮；确认/点选后执行原轨并写短说法飞轮（核词→叶）。
- 删除 prompt 中「禁止猜营养品 / 专名无把握必须空」；保留禁编造 id、禁新建类型。

**Non-Goals:**

- 不改 EVENT 梯子顺序与高置信向量阈值。
- 不扩事件表、不建表外事件类型。
- 不改 clinic / care-alert；不写测试文件。
- 不把整句（含「几点钟」）当作飞轮 document。

## Decisions

### D1：梯子为先，LLM 仅软出口

硬命中 / 多叶消歧路径不变。仅「仍空」才调 EVENT LLM。Go 已唯一命中不进 soft。

### D2：LLM 契约 = candidates

建议 JSON：

```json
{
  "candidates": [
    {"event_id": "<表内>", "event_name": "<表内>"}
  ]
}
```

- 最多 **3** 条，按相似度降序；服务端过滤非法 id。
- 空数组 = 真无解。
- 兼容：若模型仍回单字段 `event_id`，归一成单元素 candidates。

### D3：单候选 vs 多候选挂 pending

| K | pending | 话术要点 |
|---|---------|----------|
| 1 | `leaf_confirm` | predict：复述用户问法并替换事件名（「你要问的是接下来几点钟吃辅食吗？」）；create/read/delete 用既有 leaf/history 确认模板，点出候选名 |
| ≥2 | 复用 remark/parent 消歧 | options=candidates；问「辅食还是…」类 |
| 0 | 无 pending | 「无法识别…」 |

软候选段：**不得** `segment_failed` 直接 END；须 `need_confirm` + pending，确认后续跑原 TYPE（含 predict）。

### D4：删除「禁止猜营养品」

旧防的是 **静默** AD→营养品。新契约下允许模型把营养品放进 candidates，但必须确认；专名可作 `remark` 保留（与 Go 唯一命中语义对齐）。服务端仍禁止无 pending 的静默定叶。

### D5：飞轮 document = 核词

确认后 `add_event_phrase(document=核词, event_id=选定叶)`。核词优先 `remark_keyword_from_segment(段文)`（如「午饭」），空则退短说法片段；**禁止**整句 OP+时间入飞轮。未确认 / reject 不写。

### D6：与 TYPE need_confirm 的次序

EVENT soft 确认优先于「事件已定后的 TYPE 再确认」。用户先定叶，再视需要走 predict 维确认（若仍缺维）。首版：soft 确认通过后若 predict 两维已齐可直播报。

## Risks / Trade-offs

- [模型乱猜 Top1] → 多候选 K≤3 + 用户可否；reject→无法识别  
- [AD 误进辅食] → 确认话术点名叶子；飞轮仅确认后写；可 Hub 清短说法  
- [软确认与无法识别文案混淆] → soft 路径禁止走 `event_unresolved` 短复  
- [飞轮污染] → 只写核词；与既有短说法阈值一致  

## Migration Plan

1. 改 prompt + 解析 + pending 出口 + 确认后飞轮。  
2. 手工：「午饭」预测问 → 软确认辅食 → 是 → 播报/估时 + 飞轮；再问「午饭」宜硬命中。  
3. 回滚：恢复 EVENT「空或唯一」+ 禁止猜营养品句；去掉 soft 出口。

## Open Questions

（无：K=3、核词飞轮、删禁止猜营养品、多候选优先已在探索拍板。）
