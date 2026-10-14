## Why

段 EVENT 维在词典 / 别名 / 向量 / Go 反查均未硬命中时，EVENT 小 LLM 被要求「无把握则空、禁止猜营养品等类别」，于是「接下来几点钟吃午饭」虽 TYPE 已能判为预测问，却因「午饭」未静默升格为表内「辅食」而直接「无法识别对应的事件」。架构上应允许**表内软推测 + 向用户确认**，确认后再执行与飞轮，而不是硬失败。

## What Changes

- EVENT 梯子（词典 → `extra_names` → 短说法向量高置信 → Go 备注反查）**仍为先**；仅梯子未得唯一叶时进入 EVENT 小 LLM。
- EVENT 小 LLM 改为输出表内 **candidates（1..K，最像优先）**；删除「禁止猜营养品 / 专名无把握必须空」类硬空提示（仍禁止编造表外 id、禁止新建事件类型）。
- **单候选**：进入叶子软确认（如 predict：「你要问的是接下来几点钟吃辅食吗？」）；**多候选**：复用既有消歧 pending（options）。
- **未确认**不得执行播报/落库，不得写事件短说法飞轮；**确认/点选后**写入短说法飞轮（核词如「午饭」→ 选定叶），便于下次硬命中。
- candidates 为空时仍可「无法识别」；MUST NOT 回退满血 classify。

## Capabilities

### New Capabilities

- `event-soft-candidate-confirm`：EVENT 软候选（单确认 / 多消歧）、分轨确认话术、确认后短说法飞轮与禁止静默执行

### Modified Capabilities

- `intent-dim-llm-fallback`：EVENT 小 LLM 契约由「唯一表内 id 或空」改为「表内 candidates」；废止「专名无证据必须硬空、禁止猜营养品」作为硬失败条件（改由软确认承接）

## Impact

- `app/feeding/graphs/nodes/prompts/system.py`：`SEGMENT_EVENT_LLM_PROMPT`
- `app/feeding/services/segment_dim_llm.py`：`llm_resolve_event` 解析 candidates
- `app/feeding/services/segment_multidim.py`：空事件出口 → soft pending，而非立刻 `event_unresolved`
- `app/feeding/graphs/nodes/resolve_segments.py` / `clarification.py` / `intent_pipeline.py`：挂 leaf_confirm 或 remark/parent 消歧；predict/create/read 话术
- `app/feeding/services/intent_cache_store.py`：确认后 `add_event_phrase`
- 相关 OpenSpec：`intent-dim-llm-fallback` 既有 Scenario「专名无证据不升格」需 delta 废止/改写
- 不改 clinic 等其它产品线；不新增测试文件
