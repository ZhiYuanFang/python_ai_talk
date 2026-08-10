## 1. Clinic 提示词

- [x] 1.1 重写 `build_clinic_answer_system_prompt`（有史/无史）：育儿专家、记录必点、对话非必点、无征求肯定、无强制抛话头/同月龄代入；保留点查汇总与安全边界并缩短文案
- [x] 1.2 重写 `_clinic_closing_instruction` 与喂养/对话块说明：有记录则必点 1 条；有对话不强制点名；删除征求肯定与闺蜜收尾
- [x] 1.3 更新 `clinic_answer.py` 文件/函数中文注释口径

## 2. Tip 提示词

- [x] 2.1 重写 `build_tip_answer_system_prompt`：育儿专家开场；记录必点；对话非必点；短；安全；无闺蜜剧本
- [x] 2.2 重写 `_tip_closing_instruction` 与历史块说明：对齐 clinic 有据不对称规则；无征求肯定
- [x] 2.3 更新 `tip_answer.py` 文件/函数中文注释口径

## 3. 校验

- [x] 3.1 确认 intent 共用 `clinic_answer` 无需另改即可走专家文案
- [x] 3.2 `openspec validate expert-tone-clinic-tip --strict` 通过
