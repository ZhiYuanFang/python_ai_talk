## 1. 规则与提示

- [x] 1.1 抽出/扩写结束口语线索（含醒了、睡醒、起床等），TYPE 在喂养线索之前优先匹配 end；与 SHAPE 共用常量
- [x] 1.2 在 `prompts/system.py` 增加 `SEGMENT_SHAPE_LLM_PROMPT`（create+start / end+end / create+one；睡着 vs 睡醒对照）

## 2. SHAPE LLM 与挂接

- [x] 2.1 `segment_dim_llm.llm_resolve_shape`：stream 收集、解析、校验枚举
- [x] 2.2 `resolve_segment`：time 叶在规则推导后，无明确 end 且存在暧昧/未覆盖结束态时调 SHAPE LLM；回写 op/action；`rule_gap(llm_used=True)`
- [x] 2.3 明确结束线索命中时不调 LLM，直接 end

## 3. 验收

- [ ] 3.1 手工：睡醒了→结束睡眠确认；睡着了→开始；「结束睡眠」→ end；确认文案无「现在开始」误用
