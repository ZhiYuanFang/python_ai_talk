## Context

`intent-segment-multidim` 将意图主路径改为分句 + 段多维，但 EVENT 仅词典包含匹配与短说法向量，未接 `extra_names`、未接 Go 备注反查，拼装里 `remark` 恒空。旧 `resolve_remark_event`（有名无 id → filter）已不在图上。产品需要：实例词定类别事件、自由明细进备注、Hub 不新开别名页。

## Goals / Non-Goals

**Goals:**

- EVENT：词典 → extra_names → 向量 → Go 备注反查。
- extra_names 命中：`event_id`=所属事件，`remark`=命中别名词。
- 全事件可带自由明细：事件已定后小 LLM 抽 `remark`（可空）；与别名命中合并策略明确。
- Hub 只维护字典 extraNames，Python 只读缓存匹配。

**Non-Goals:**

- 独立别名 MySQL 表或新 Hub CRUD。
- 用规则从「有点黄」硬截备注。
- 恢复满血一次结构化 classify。

## Decisions

### D1：extra_names = 类别/实例别名

命中规则：对段文本（及可选剥动词后的核心词）与全表各事件 `extra_names[]` **精确**比较（可做 strip/去「了」轻归一）。多事件同时命中同一别名 → 消歧或记缺口（实现取消歧 pending 优先）。

**Alternatives：** 独立别名表——否决（Hub 已能改 extraNames）。

### D2：EVENT 阶梯

```
1) event_name 词典匹配（现有）
2) extra_names 精确 → 定事件 + remark=别名
3) 短说法向量 ≥0.72
4) await Go remark filter(keyword=段或核心词)
   唯一叶 → 定事件 + remark=keyword
   多叶 → 备注消歧 pending
   零 → 段失败/重说 + rule_gap event
```

### D3：自由明细 LLM

事件已定后调用小 LLM：输入段原文 + 已定 event_name；输出 `{remark}` 可空。  
若步骤 2/4 已写入 remark：LLM **MAY 合并/补充**（实现默认：已有非空别名 remark 则跳过 LLM，避免「菠菜」被冲掉；若段内另有「有点黄」类描述则 SHALL 再调 LLM 并将结果与已有 remark 用顿号拼接或以后者为准——**默认拼接**：`已有 + "，" + 新` 若新非空且不包含于已有）。

更简单默认（实现采用）：**别名/反查已有 remark 则仍调用 LLM**；若 LLM 返回空保留已有；若返回非空且与已有不同则 `已有，LLM`（去重包含关系）。

### D4：与单事件零 LLM

为明细抽取，事件已定后 **SHALL** 调用备注小 LLM（可返回空）。即单事件不再保证全程零 LLM，但分句与满血 classify 仍不恢复。

### D5：异步

`resolve_segments` 已是 async；EVENT miss 的 Go 反查在段循环内 await；可按专名缓存避免同句重复 HTTP。

## Risks / Trade-offs

- [extra_names 一词多事件] → 消歧或拒配并缺口  
- [整段当 remark keyword 噪声] → 优先短段/核心词；长段先剥钟点量词再查  
- [LLM 延迟] → 提示极短；空 remark 廉价  
- [与 multidim 并行] → 本 change 任务标明依赖多维模块文件  

## Migration Plan

1. 实现 Python 匹配与 LLM、反查挂接。  
2. Hub 向辅食等事件批量填 extraNames（运维，非本仓代码）。  
3. 验收：菠菜→辅食+备注；尿尿有点黄→备注；AD 历史反查。

## Open Questions

- 一词多事件：消歧 vs 直接失败（默认消歧）。  
- 别名 remark 与 LLM remark 拼接符（默认中文逗号）。
