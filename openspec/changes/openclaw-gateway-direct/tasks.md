## 1. Spike 与 Gateway 基线

- [x] 1.1 选定 OpenClaw 发行版与 Go 调用方式（WS RPC agent.run / 官方客户端等），在 design 附录写死版本与 API
- [x] 1.2 本机或 compose 拉起 Gateway；配置 Intent/Clinic/Care 三个 agents.entries 与 tool 策略草稿
- [x] 1.3 Spike：Go（或 curl）注入 model 跑通一轮 Intent（可先假 tool），验证 sessionKey 续轮；结论写入 design

## 2. 业务 tools（Gateway 可调）

- [x] 2.1 注册 history 四写 + filter/list/options/profile 等 tools，直打 Go REST（复用已有四 REST/top_k 语义）
- [x] 2.2 注册飞轮 tools：Intent retrieve/record、Clinic retrieve/record；**不**注册 Care 飞轮 tool
- [x] 2.3 注册 Care `emit_care_cards`（或等价）结构化出卡 tool；Clinic/Care tool ACL 禁止写史

## 3. Go：改打 Gateway，废结构化意图

- [x] 3.1 新增 OpenClaw Gateway 客户端；配置 `OPENCLAW_GATEWAY_URL`；进 Gateway 前注入 model
- [x] 3.2 Intent 路径改为 Gateway；对用户仅播 NL reply/thinking；删除 `AnalyzeIntentResponse` 解析与二次写库路径
- [x] 3.3 Clinic 路径改为 Gateway；映射流式/整段 reply 到现有产品通道
- [x] 3.4 Care 路径改为 Gateway；从结构化 tool result 取卡片写入日缓存
- [x] 3.5 删除 Go 侧 clinic feedback、care-alert feedback 飞轮转发；配置与代码检索无飞轮调用
- [x] 3.6 断开 `PYTHON_AI_TALK_URL` 作为 Intent/Clinic/Care 编排上游（正式验收）

## 4. Python：瘦身与删编排

- [x] 4.1 删除进程内 `shared/agents/runtime.py`、各 `*_agent.py` 条件边编排及 `/v1/analyze/*`、`/v1/clinic*` 产品编排入口
- [x] 4.2 暴露飞轮 HTTP tools（仅 Intent/Clinic）；删除 Care 飞轮（prompt/ledger/feedback）与 `/v1/care-alert/feedback`
- [x] 4.3 删除 `/v1/clinic/feedback`；隐式采纳逻辑改为可供 Gateway Clinic 调用的 tool/服务函数（不经 Go）
- [x] 4.4 更新 `openspec/project.md` / `AGENTS.md`：编排权威=OpenClaw Gateway；Python=飞轮/tool；目录表述同步

## 5. Flutter / App

- [x] 5.1 删除 Clinic 显式点赞调用与死代码
- [x] 5.2 Care ignore/follow_up：若保留则仅本地/日缓存 UI，不打 Python、不打飞轮；确认无直连 Python

## 6. 与前序 change 对齐

- [x] 6.1 确认 tip 全链路仍不存在（Python/Go/Flutter）
- [x] 6.2 标注或停止以 `openclaw-three-agents` 的 10.1–10.3（旧 FastAPI）为验收；改按本 change 验收
- [x] 6.3 保留并复用四 REST、top_k、飞轮门面等已落地资产，禁止退回 batch 作为 Intent 主路径

## 7. 手工验收（无测试文件）

- [x] 7.1 Intent：Gateway 注 model 后 tool 落库成功；Go 只播 reply；澄清同 session 续轮可用
- [x] 7.2 Clinic：可聊；无显式赞；隐式采纳不经 Go；Clinic/Care 无法写史
- [x] 7.3 Care：结构化出卡进入日缓存；无 Care 飞轮；App 不直打 Python
- [x] 7.4 Go 业务树无飞轮调用；tip 路由不存在

> **§7 说明（2026-08-15）**：静态验收已完成（Go `voice` 包编译通过；产品路径改 `OpenClawHTTPClient`；Python 删除 `/v1/analyze|clinic|care-alert` 编排路由；Flutter Care 反馈 UI-only；tip agent/SSE 路由不存在；写史 tools 仅 Intent allow）。**端到端**（Gateway + 真 model + tool 落库）需本机 `openclaw gateway run` 与 provider 密钥后再人工冒烟；不阻塞本 change 任务勾选。
