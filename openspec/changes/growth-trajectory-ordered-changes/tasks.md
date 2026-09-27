## 1. 提示词

- [x] 1.1 更新 `GROWTH_TRAJECTORY_SYSTEM_PROMPT`：任务强调有序可能变化；字数约 400～600；保留中文思考与非诊断
- [x] 1.2 更新 `generate` user：主段编号阶梯；禁日历日主结构；注意/喂养为辅
- [x] 1.3 更新 `plan` user：挖能力边界；choice=2；细挖 free_text；enough 不表示跳过末问

## 2. 编排

- [x] 2.1 `plan_next`：enough 且未 `final_ask_done` 时改为 `final_ask` 并写入 free_text 兜底题（不得直 generate）
- [x] 2.2 确认满轮强制 final、final 后 generate 路径仍正确；末问文案含「最后一次」与自述引导

## 3. 校验

- [x] 3.1 `openspec validate growth-trajectory-ordered-changes --strict` 通过
