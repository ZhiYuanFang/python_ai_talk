## 1. System 提示词

- [x] 1.1 更新 `app/growth_trajectory/graphs/nodes/prompts/system.py`：在 `GROWTH_TRAJECTORY_SYSTEM_PROMPT` 约束列表增加「内部思考（reasoning）须使用中文」
- [x] 1.2 同步更新该文件头业务说明：去掉「不指导思考写法」，改为说明已约束思考语言为中文

## 2. 核对与验收

- [x] 2.1 确认 `confirm_prior` / `plan_next` / `generate`（及 ask 兜底）仍引用同一 `GROWTH_TRAJECTORY_SYSTEM_PROMPT`，无需改调用点
- [ ] 2.2 手工跑一轮成长轨迹流式对话：观察 SSE `thinking` 中 LLM reasoning 增量是否主要为中文；编排字幕与 question/result 行为不变
