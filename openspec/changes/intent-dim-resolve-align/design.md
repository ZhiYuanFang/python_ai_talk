## Context

`intent-crud-other-reframe` 已引入 create|read|update|delete|exit|other 与 OP / qty / read_source 整段飞轮；时间无飞轮。审计发现：各维判定手写分叉，未共用同一方法；`history_speak` 仍短词热路径；无 `feeding_predict_cues` / `feeding_locate_cues`；事件 LLM 成功不整段回写。用户拍板：**history_speak 硬切整段**。

约束：中文注释；禁止测试文件；feeding 内实现；一期仍 Go batch；TIME 继续规则+rule_gap。

## Goals / Non-Goals

**Goals:**

- 各飞轮维判定统一为：可选规则 → 整段飞轮 → 维 LLM → 整段回写（TIME 例外写 gap）。
- history_speak **硬切**整段 document；停用短词命中与短词回写。
- 补齐 R·predict、U/D 定位整段飞轮；predict 两维可独立热路径跳过 LLM。
- 事件冷路径成功整段回写，与 OP/qty 同构。
- 整句种子与 admin 契约对齐。

**Non-Goals:**

- 不抽重量级 Base Class / 共享 SentenceTransformer 基建（可薄封装调用形状；基建复用另议）。
- 不恢复短关键词 TYPE 热路径。
- 不做时间向量飞轮。
- 不拆 Go create/update/delete 独立 HTTP。
- 本仓不实现 Hub 前端（任务可标兄弟仓）。

## Decisions

### D1：统一维判定形状（方法复用，非基建复用）

每个飞轮维提供显式 `resolve_<dim>(segment, …)`，逻辑顺序固定：

```
① 维相关强规则/词典（可选）
② 整段飞轮命中且 payload 合法 → 返回，跳过本维 LLM
③ 维小 LLM
④ 成功 → 以段整句为 document 回写飞轮
⑤ 失败/缺槽 → clarify；不写飞轮
```

时间维：`① 规则 → ③ TIME LLM → ④ rule_gap`（关闭②④飞轮）。

**Alternatives：** 仅文档约定不改代码结构 — 否决（易再分叉）。抽抽象基类 store — 本期 Non-Goal。

### D2：history_speak 硬切整段

- Collection 可保留 `feeding_history_speak_cues` 或演进为 `feeding_read_speak_cues`；**document MUST 为段整句**。
- 命中策略对齐 OP：阈值从严；非全文相等须更高分。
- **删除/停用** `add_keywords` 作为主回写；LLM 成功只 `add(整段原文, payload)`。
- 清空或忽略旧短词条目；种子改为整句（「睡了多久了」等）。
- **不**保留「短词只读过渡期」（用户拍板硬切）。

**Alternatives：** 整段优先+短词 legacy — 否决。

### D3：R·predict 独立层

- `feeding_predict_cues`：document=整段；payload=`predict_channel` + `time_answer`。
- `resolve_predict_dims`：飞轮 →（缺）维 LLM → 回写；由 read+predict 路径调用，不再仅依赖 OP LLM 打包两维。
- OP 飞轮仍只存 `op_rail`；source 仍 `read_source`；预测两维本层负责。

### D4：U/D 定位独立层

- `feeding_locate_cues`：document=整段；payload=策略码（如 `latest` / `open_timer` / `prefer_completed`），**禁止**存 historyId。
- `resolve_locate`：飞轮 → LLM → 回写；执行时再按策略查史选行。
- U·end 无 open → 转 C：保持 reframe 行为，可与 locate=`open_timer` 组合。

### D5：事件回写对齐

- `resolve_event` 在 LLM（或等价冷路径）成功定叶后，以**段整句**写入 `feeding_intents`（或现行事件短说法集合的整段模式），与 qty/OP 同构。
- 词典/alias 热命中可不写；向量已命中不重复写。

### D6：与 reframe 关系

- 本 change **补齐并校正** reframe 未完成的飞轮契约；不回退六轨枚举。
- reframe tasks 中「勾了但短词/缺层」的项以本 change 为准收口。

## Risks / Trade-offs

- [硬切后冷启动播报多打 LLM] → 整句种子 + 成功回写；接受严阈值
- [旧短词库噪声] → 发版清空或过滤长度/形态不合整段的 document
- [predict 与 OP LLM 双写两维] → 热路径只读 predict_cues；OP LLM 仅在 OP/source 未齐时调用，成功后拆写各层
- [locate 策略过粗] → 先少量策略码；多候选仍 clarify

## Migration Plan

1. 部署新 resolve 形状与 predict/locate store；history_speak 改为整段读写。
2. 清空/失效短词 speak 条目；跑整句种子（含 OP/source/speak/predict）。
3. 金线手工：睡了多久了 / 还有多久醒来 / 睡醒了 / 口语量二次。
4. 回滚：恢复短词 speak 读写（应急）；六轨与 OP/qty 可保留。

## Open Questions

（无：history_speak 硬切已定；基建级 store 复用另开 change。）
