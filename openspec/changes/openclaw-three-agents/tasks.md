## 1. Python：删除 tip 与路由残留

- [x] 1.1 删除 `app/tip/**`、`app/api/routes/tip.py`，并从 `app/api/routes/__init__.py` / `main` 卸载 tip 路由
- [x] 1.2 清理 companion_session 中 tip 合成开场写入与 tip|clinic 共享表述；仅保留 clinic 会话语义（中文注释同步）
- [x] 1.3 全局检索并移除对 tip_graph / TipRequest / tip_stream 的引用

## 2. Python：业务 tool 客户端（四写 + 读）

- [x] 2.1 在 `http_client`（或 `shared/tools`）实现/对齐 create、update、delete、end 单动词调用，字段与 Go add/update/delete/end-latest 契约对齐，补中文注释
- [x] 2.2 Intent 确认落库路径改为多次单动词调用；同轮先 end 后其余；停止经 `batch_history_events` 作为意图写入口
- [x] 2.3 update/delete 无行 id 时经 filter/latest 解析目标行；失败原因可进入模板回执
- [x] 2.4 配置项支持业务 API base URL 重绑；文档/注释标明飞轮基址不可被同一机制覆盖

## 3. Python：读史 top_k

- [x] 3.1 `IntentEventItem`（或等价）增加 `top_k`（默认 1，上限 ≤5）；normalize 保留该字段
- [x] 3.2 更新意图分类 prompt：「前两次」→ top_k=2；「上一次」→ 1；可与 ignore_time_range 组合
- [x] 3.3 重写查记录播报：按 start_time 倒序取前 k 条列举模板；不足 k 条如实说明；禁止再捏成单条「上一次」当 k>1
- [x] 3.4 filter 客户端在 Go 未改前可做稳定二次排序过渡，并注明目标态依赖 Go `ORDER BY start_time DESC`

## 4. Python：飞轮门面与隔离

- [x] 4.1 引入 flywheel retrieve / record_outcome（或等价）门面；Intent/Clinic/Care Alert 只经门面访问各自仓
- [x] 4.2 Intent 缓存改为可移植结构（说法 + 名/动作等）；命中后经事件字典解析 id 再写
- [x] 4.3 确认飞轮基址配置锁定我方；三仓 key/collection 互不写入；去掉 tip 对 clinic 飞轮的输入路径

## 5. Python：去 LangGraph，换 Agent 运行时

- [x] 5.1 Spike：选定 OpenClaw 接入方式（Gateway 侧车或进程内等价 LLM+tool loop），结论写入 design 开放问题关闭说明（注释或 design 附录）
- [x] 5.2 实现 Intent Agent 运行时替换 `intent_graph`；路由 `/v1/analyze/intent`（及 stream 若保留）改调 Agent；保留外侧 conversation_id + pending
- [x] 5.3 实现 Clinic Agent（只读 tool）替换 `clinic_graph`；保留 `/v1/clinic` 与 stream 产品帧契约
- [x] 5.4 实现 Care Alert Agent（只读 + 卡片输出）替换 `care_alert_graph`；保留 analyze/feedback 入口
- [x] 5.5 删除各 `*_graph.py`、StateGraph 注册、仅为图 custom thinking 且无用的适配代码；从 `pyproject.toml` 移除 `langgraph` 依赖
- [x] 5.6 更新 `openspec/project.md` / `AGENTS.md`：技术栈 LangGraph→OpenClaw；目录去掉 tip；模块分离保留 feeding/clinic/care_alert/shared

## 6. Python：删除仅为 LangGraph 匹配的废 API/胶水

- [x] 6.1 清点并删除无产品调用方、仅为 LangGraph 流式/检查点/图调试存在的内部 API 或死路由
- [x] 6.2 删除 Intent 对 batch 客户端方法的调用路径后，若 `batch_history_events` 已无引用则删除或标废弃（本仓）；不强制删 Go batch 路由

## 7. 配置：settings + .env.prod / example / compose

- [x] 7.1 `settings.py` 增加 `go_api_base_url`、`flywheel_base_url`、`history_read_top_k_max`、可选 `openclaw_gateway_url`；删除或停用未使用的 `device_service_url`；注释去掉 tip 共享表述
- [x] 7.2 重写 `env/.env.prod`：删除 `DEVICE_SERVICE_URL`、`VOICE_SERVICE_URL`；设置 `GO_API_BASE_URL=https://www.pangbao.cuplay.top`、`HISTORY_SERVICE_URL=https://www.pangbao.cuplay.top`；补齐 `FLYWHEEL_BASE_URL=`、`HISTORY_READ_TOP_K_MAX=5`、`CARE_ALERT_*`、`OPENCLAW_GATEWAY_URL=`；**保留**原镜像/Redis/LLM/ACR 等密钥与标签赋值不改值
- [x] 7.3 同步 `.env.example`（及必要时 `env/.env.test` 结构键名）与 `docker-compose.yml` 注入键，三层同名；compose 去掉已删变量
- [x] 7.4 手工确认：prod 文件无 tip/LangGraph 废变量；Go 两基址无尾斜杠且为胖宝域名

## 8. Go（跨仓 `go_ai_talk`）：补齐与删除

- [x] 8.1 filter 主排序改为 `start_time DESC`（或等价），满足前 k 次发生语义
- [x] 8.2 校对 add/update/delete/end-latest 与原 batch 子项字段（action/start|one、end、remark、错误 reason）差距并补齐
- [x] 8.3 删除 TipStream、TipCtrl、`/device/tip/*` 注册、gateway tip 反代及无用 tip feedback（确认无调用方）
- [x] 8.4 文档/OpenSpec（Go 仓）标明 Agent 写路径使用四 REST，不再依赖 batch

## 9. Flutter（跨仓 `flutter_ai_talk`）：删 tip 死代码

- [x] 9.1 删除 `tip_repository` / `tip_provider` / `home_tip_panel` / `tip_models` 等 tip SSE 死代码及无用 import
- [x] 9.2 确认保留 `widget_tip_*` 与 Care Alert→桌面 tip 路径；主路径无 `/device/tip/generate` 调用

## 10. 验收（手工，无测试文件）

> **已废止为本 change 验收依据**：请改用 `openclaw-gateway-direct` tasks §7。
> 下列 10.1–10.3 针对旧 FastAPI 编排，不再作为达标条件。

- [ ] 10.1 Intent：确认后 create/update/delete/end 分调成功；多事件先 end 后写；conversation_id 续轮可用
- [ ] 10.2 Intent：问「前两次…分别何时」播报两条时间；「上一次」仍单条
- [ ] 10.3 Clinic 只读可聊；Care Alert 出卡片；二者无法写史
- [x] 10.4 tip 路由 404/不存在；widget tip 仍可用（静态：Python/Go/Flutter 均无 tip SSE；widget_tip_* 保留）
- [x] 10.5 飞轮：三仓隔离；业务 URL 重绑后飞轮仍打我方（静态：门面 + flywheel_base_url 锁定）
- [x] 10.6 `env/.env.prod` 中 `GO_API_BASE_URL`/`HISTORY_SERVICE_URL` 均为 `https://www.pangbao.cuplay.top`，且无 DEVICE/VOICE 废变量
