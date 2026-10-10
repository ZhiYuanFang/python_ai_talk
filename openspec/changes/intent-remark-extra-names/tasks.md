## 1. EVENT：extra_names 与阶梯

- [x] 1.1 在段事件匹配模块增加全表 `extra_names` 精确命中（轻归一：strip/去句末「了」等），唯一命中返回 `event_id`/`event_name`/`remark=别名`；多命中走消歧 pending
- [x] 1.2 调整段 EVENT 阶梯顺序：词典名 → extra_names → 短说法向量(0.72) → Go 备注反查；中文注释标明阶梯与禁止常识升格

## 2. 段级 Go 备注反查

- [x] 2.1 复用既有 filter/`resolve_remark_event` 聚合消歧逻辑，挂入段循环：keyword=段或剥钟点量词后的核心词；唯一叶写回事件+remark；多叶消歧；零命中段失败/重说并记 rule_gap（若多维已有缺口通道）
- [x] 2.2 同句重复 keyword 可短缓存，避免重复 HTTP；保持 async，不阻塞整图同步假流式

## 3. 明细备注 LLM

- [x] 3.1 在 `prompts/system.py` 增加段明细备注抽取常量（中文 system；输出可空 `remark` JSON/短文本约定）
- [x] 3.2 事件已定后调用小 LLM（SSE 路径 `stream(thinking_enabled=True)` 透出 reasoning）；与已有 remark 按设计合并（空则保留别名/反查；非空拼接去重）
- [x] 3.3 拼装意图项与确认话术、batch payload 写出非空 `remark`（batch 字段已存在则填满）

## 4. 验收与边界

- [ ] 4.1 手工验收：菠菜→辅食+remark；尿尿有点黄→remark；AD 历史反查；别名命中后空 LLM 不冲掉 remark（需 Hub 填好辅食 extraNames 与近窗历史后联调）
- [x] 4.2 确认无新 Hub 别名页/无新别名表；Hub 仅靠既有字典 extraNames 维护即可运维
