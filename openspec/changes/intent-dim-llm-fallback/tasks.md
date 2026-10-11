## 1. 提示词与维级 LLM 模块

- [x] 1.1 在 `prompts/system.py` 增加 TYPE / EVENT / TIME / QTY 四段小 LLM 中文常量（窄 JSON 契约；EVENT 禁编造与专名升格）
- [x] 1.2 新增 `segment_dim_llm.py`（或等价）：四异步函数经 `stream_llm_collect(thinking_enabled=True)`；解析失败返回空/未解析

## 2. 挂入段多维

- [x] 2.1 TYPE：规则无线索/冲突且无句级 type 时调 TYPE LLM；写 `rule_gap(llm_used=True)`
- [x] 2.2 EVENT：Go 反查零命中（且非多叶消歧）后调 EVENT LLM；命中则定事件；仍空再失败重说；写 gap+`llm_used`
- [x] 2.3 TIME：半命中或有时间线索无可用 unix 时先弃权残缺规则时间再调 TIME LLM；写 gap+`llm_used`
- [x] 2.4 QTY：有量线索但规则抽空时调 QTY LLM；无量线索的 number 叶仍缺量追问不调 LLM；写 gap+`llm_used`（若调用）

## 3. 文案与衔接

- [x] 3.1 更新模块注释/单事件语义：零分句与零满血，维级小 LLM 可按需
- [x] 3.2 确认与 `intent-remark-extra-names` 顺序一致：extra_names → 向量 → Go → EVENT LLM → 明细备注 LLM

## 4. 验收

- [ ] 4.1 手工：睡着了→睡觉/睡眠确认；AD 无史→不升格；昨晚6点类半命中不落成今天早上；number 无量仍追问
