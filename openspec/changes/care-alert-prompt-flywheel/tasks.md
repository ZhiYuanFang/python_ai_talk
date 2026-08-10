## 1. 配置与挂载

- [x] 1.1 在 `settings` / `.env.example` 增加 `CARE_ALERT_PROMPT_DIR` 及可选飞轮上限/重写阈值配置（无 `PYTHON_AI_TALK_` 前缀）
- [x] 1.2 基线 `docker-compose.yml` 增加 `./data/care_alert:/app/data/care_alert`（或等价）挂载
- [x] 1.3 更新 `docs/deploy-guide.md` 环境变量清单与 volume 说明

## 2. 本地 prompt 存储

- [x] 2.1 新增 care_alert 本地 prompt/ledger 读写模块（加载、缺失 bootstrap、原子写、文件锁、可选 `.bak`）
- [x] 2.2 定义默认模板：`output_format` + 空 `contrastive_examples`；月龄/历史不落盘，仅运行时拼接
- [x] 2.3 落盘前校验：拒绝含具体月龄实例行或历史流水正文的非法重写

## 3. Analyze 去知识库并接本地 prompt

- [x] 3.1 修改 `care_alert_graph`：去掉 `search_vectors` 节点与边
- [x] 3.2 改写 `care_alert_analyze` prompt 组装：读本地静态块 + 运行时注入月龄/历史/legend；移除知识摘录块与 `kg_context` 硬塞
- [x] 3.3 更新 `generate_care_alerts` / `analyze` 服务：不再依赖 `knowledge`；清理相关日志与 state 字段用法
- [x] 3.4 将 `flywheel_store` 从 `knowledge_ids` 改为 suggestion 快照（TTL 可配置）；analyze 成功后按 item 写入

## 4. Feedback 对比样例飞轮

- [x] 4.1 改写 `/care-alert/feedback`：按快照 + intent 追加 ledger；不再调用通识 `update_quality_score`；失败仍 ACK
- [x] 4.2 实现按 `(type/event, 信号档)` 聚合与对比样例渲染（✓/✗/⚡）；低证据槽省略
- [x] 4.3 实现长度上限与触发重写（达 N 条或间隔）；超限则裁剪/中止写并保留旧 prompt
- [x] 4.4 更新 schemas/路由模块中文注释与 CONTRACT（若本仓有 care-alert CONTRACT）说明飞轮语义变更

## 5. 收尾核对

- [x] 5.1 确认 care_alert 路径无向量知识检索、无通识质量更新；clinic 通识飞轮未误改
- [x] 5.2 `openspec validate care-alert-prompt-flywheel --strict` 通过
