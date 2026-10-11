## 1. 飞轮存储与 Admin

- [x] 1.1 新增 `feeding_history_speak_cues` store：search/add/list/bulk 跳过/dedupe/delete；payload=`point_pick`/`open_speak`；中文注释
- [x] 1.2 新增 `/v1/admin/history-speak-cache`（list/bulk/dedupe/delete），注册路由
- [x] 1.3（兄弟仓）Go Hub：查史播报向量整理页 + 反代 — 本仓跳过，兄弟仓跟进

## 2. 小 LLM 与提示词

- [x] 2.1 `prompts/system.py` 增加查史播报小 LLM 常量；纠偏「多久了」→ latest+elapsed、「上次」→ prefer_completed；SSE 真流式 + 中文 reasoning
- [x] 2.2 实现解析：两维校验；非法/失败不写飞轮；keywords 灌库时机（直播、不强制确认）

## 3. speak_history 落地

- [x] 3.1 点查前解析策略：飞轮命中合法则用；否则必调 LLM；禁止缺维静默 prefer_completed
- [x] 3.2 按 `point_pick` 选行（latest / prefer_completed）；父塌缩与多叶点查共用
- [x] 3.3 进行中：`elapsed` 报 now−start；`in_progress` 沿用固定话术并可拼 ETA；有 end 仍用既有用时
- [x] 3.4 LLM 失败：明确降级话术，不回落无条件优先已完成

## 4. 种子与验收

- [x] 4.1 bulk/脚本种子：「多久了」「睡了多久」→ latest+elapsed；「上次」「上一次」→ prefer_completed+in_progress（或产品微调）
- [ ] 4.2 手工：进行中睡眠 +「睡了多久了」→ 最近开表 + 已持续（非上一笔完整用时）
- [ ] 4.3 手工：「上次睡眠」类 → 仍可优先已完成；predict「还有多久醒来」不进本飞轮
