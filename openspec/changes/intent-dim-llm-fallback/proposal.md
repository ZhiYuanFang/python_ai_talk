## Why

段多维设计已约定 TYPE / EVENT / TIME / QTY 在规则 miss 后走**窄契约小 LLM 兜底**，但实现只落了规则 + `rule_gap`，EVENT 在 Go 备注反查零命中后直接「无法识别」。口语如「睡着了」无法对齐表内「睡觉/睡眠」，时间半命中也不会再问模型，与 `intent-segment-multidim` D2 及缺口规格中的「调用 LLM 兜底」不一致。

## What Changes

- 段流水线在规则（及 EVENT 既有阶梯）之后补齐维级小 LLM：**TYPE、EVENT、TIME、QTY**；SHAPE 仍纯推导；明细备注 LLM 保持 `intent-remark-extra-names` 已有行为。
- EVENT 阶梯终局前增加：词典 → extra_names → 向量 → Go 备注反查 → **事件小 LLM** → 仍空才引导重说（口语对齐表内叶；禁止专名常识升格）。
- TYPE / TIME / QTY：规则 miss 或时间半命中等触发时调用对应小 LLM；契约只解该维；SSE 真流式 + 中文 reasoning；提示词落 `prompts/system.py`。
- 走兜底时 `rule_gap` MUST 带 `llm_used`（及可选结果摘要）；number 叶完全无量仍走缺量追问，不靠 LLM 瞎填。
- MUST NOT 恢复满血一次多 events `classify_intent` 主路径；单事件仍跳过分句 LLM。

## Capabilities

### New Capabilities

- `intent-dim-llm-fallback`：段维 TYPE / EVENT / TIME / QTY 窄契约小 LLM 触发条件、输出契约、与规则/缺口/失败重说的衔接

### Modified Capabilities

- `intent-segment-multidim`：单事件「零 LLM」改为零满血/零分句，允许维级小 LLM；EVENT 顺序含小 LLM 兜底
- `intent-segment-remark`：明确 Go 反查零命中后进入事件小 LLM，而非直接终局无法识别（与备注 change 衔接）
- `intent-rule-gap-inbox`：兜底调用时必须标记 `llm_used`（相对未收版 multidim 缺口约定的强化）
- `intent-event-phrase-flywheel`：向量未达门槛后进入事件小 LLM（对齐原规格已写、未实现的路径）

## Impact

- **Python**：`segment_multidim` / `resolve_segments`、新维级 LLM helper（或 `segment_dim_llm`）、`prompts/system.py` 四常量、`rule_gap_store` 写入带 `llm_used`。
- **依赖**：宜叠在段多维 + `intent-remark-extra-names`（extra_names / Go 反查 / 明细备注）之上。
- **Go / Hub**：无新表；缺口页仍读既有 admin API。
