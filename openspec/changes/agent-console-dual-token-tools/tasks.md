## 1. 数据模型与配置骨架（Python）

- [x] 1.1 新增 MySQL 连接配置（与 Go 同址约定）；去掉产品默认 `GO_API_BASE_URL` / `HISTORY_SERVICE_URL` / Python 侧 `OPENCLAW_GATEWAY_URL` 业务含义
- [x] 1.2 建表（或迁移）：租户/用户备注、G token 哈希与 enabled、A token 哈希、G↔A 1:1、tool 槽位完整 URL 与可选上游鉴权
- [x] 1.3 管理员种子账密与内部 Gateway secret 的环境变量；Token 只存哈希、生成时返回明文
- [x] 1.4 静态 Tool Contract Catalog（槽位、方法、入参/出参/必填说明）

## 2. 塑形 History Tools（Python）

- [x] 2.1 扩展 `/v1/tools`：history 四写 + filter/list/options + baby_profile；按 A 查 URL 转发上游
- [x] 2.2 读路径挂接 `baby_age` / `history_prompt_fields`（或等价）输出瘦 JSON；写路径短回执
- [x] 2.3 收敛 `http_client` 为「按完整 URL 调上游」；无 URL / 无有效 A 时明确失败
- [x] 2.4 更新 `.env.example` / `env/.env.prod` / compose：DB 与管理员相关；删除误导性默认业务上游与死 Care 飞轮 env（若仍无引用）

## 3. 插件与 Gateway 配置

- [x] 3.1 `pangbao-tools`：history_* / baby_profile 改为只打 `toolsBaseUrl`；转发 A 头；废弃 `historyBaseUrl` 产品路径
- [x] 3.2 更新 `openclaw.json5` / 插件 README / 工作区 AGENTS 中与「直打 Go」矛盾的描述
- [x] 3.3 Spike：确认自定义头能到 plugin execute；不行则按 design 备选落地并回写 design 结论

## 4. 多 G 门禁（Python 优先）

- [x] 4.1 实现门禁：校验 G∈库且 enabled → 用内部 secret 转发 OpenClaw `/v1/chat/completions`（及必要附属）
- [x] 4.2 无效/失效 G 拒绝；文档标明对外入口为门禁而非裸 Gateway

## 5. 智能体管理后台 UI

- [x] 5.1 主页：品牌「AI喂养智能体」、浅空蓝+宝宝主题；仅 G 或 A Token 进入；右上管理员入口
- [x] 5.2 管理员：账密登录；成对签发 G+A（用户名/备注）；列表；G 生效/失效；禁止 1:N
- [x] 5.3 API 管理页：展示并复制 G+A；Go 视角接入说明；槽位完整 URL 编辑；Catalog 入参出参必填只读
- [x] 5.4 会话与遮罩：Token 展示默认遮罩；复制可用

## 6. 死代码与文档对齐（塑形可用后）

- [x] 6.1 删除或掏空与直打 Go 冲突的残留注释/配置；保留塑形模块
- [x] 6.2 更新 `README.md` / `openspec/project.md` 中 History 直打 Go、默认上游等过时表述
- [x] 6.3 手工验收：无默认上游失败；手配 URL 后读写塑形；G 失效拒智能体；缺 A 无 CRUD

## 7. Go 二期（本仓 Python 就绪后）

- [x] 7.1 Go 分项配置 G 与 A（不同配置键）
- [x] 7.2 请求：Bearer/门禁用 G；独立头传 A；对齐门禁 URL
- [x] 7.3 手工验收：G 失效不可用智能体；A 缺失无 CRUD；成对配置后主路径通
