## 1. Prompt 口径（月龄 + 有史至少一条）

- [x] 1.1 更新 `prompt_store.default_output_format()`：有史+legend 时至少一条；必须结合月龄；弱信号可轻提；仅无史/无 legend 允许空列表
- [x] 1.2 更新 `care_alert_analyze` user 指引（约 77–88 行及 legend 空时说明）：去掉「不够就空」为主规则；强调月龄与至少一条
- [x] 1.3 实现 `prompt.json` version 迁移：升级默认 `output_format` 时保留已有 `contrastive_examples`

## 2. 确定性兜底

- [x] 2.1 在生成路径增加：LLM 规范化后为空且史+legend 可用时，按启发式合成一条软提醒（合法 eventId、含 followUpPrompt）
- [x] 2.2 兜底 item 写入已知 `ageMonths`；月龄未知不编造常模数字
- [x] 2.3 确认兜底产出的 item 仍走 suggestion 快照写入（飞轮可归因）

## 3. 飞轮与文档口径

- [x] 3.1 对比样例渲染或引导中避免「有史时全部不提」；弱信号表述为轻提（若需改 `prompt_flywheel` 文案则改）
- [x] 3.2 更新 care-alert CONTRACT / 模块注释中「可空列表」表述，与本变更一致

## 4. 校验

- [x] 4.1 `openspec validate care-alert-min-one-with-age --strict` 通过
