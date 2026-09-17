## 1. Care-alert：去飞轮与 feedback

- [x] 1.1 删除 `POST /v1/care-alert/feedback` 路由及相关 schema/导入；更新 `care_alert` 路由模块注释
- [x] 1.2 删除 `prompt_flywheel.py`、`flywheel_store.py` 及 analyze 中 suggestion 快照写入
- [x] 1.3 收敛 `prompt_store`：去掉 ledger / contrastive 飞轮重写 / meta 闭环；保留静态 `prompt.json` 加载与 `output_format`
- [x] 1.4 清理 care_alert 飞轮相关 settings 与 compose/文档中「ledger 必挂」口径（静态 prompt 目录可保留）

## 2. Clinic：去 Q&A 与 implicit_feedback

- [x] 2.1 从 `clinic_graph` 移除 `implicit_feedback`、rewrite/search_qa/format_qa 节点与边；调整入口到下一业务节点
- [x] 2.2 删除或停用 `qa_fast_path` 模块调用及 clinic 相关节点文件引用
- [x] 2.3 删除/掏空 `suggestion_acceptance` 中通识加减分与 Q&A promote/demote；去掉 clinic 路由对飞轮字段的依赖写入

## 3. Clinic / Tip：去通识检索

- [x] 3.1 从 `clinic_graph` / `tip_graph` 移除 `search_vectors` 挂载与边
- [x] 3.2 从 clinic/tip 回答 prompt 去掉「知识库参考」注入；state/路由不再收集 `knowledge_ids`
- [x] 3.3 更新 thinking 文案，去掉「检索相关知识」类编排字幕

## 4. Knowledge API 与向量通识/Q&A

- [x] 4.1 卸载并删除 `app/api/routes/knowledge.py` 及 `main`/routes 挂载
- [x] 4.2 从 `vector_store`（及调用方）移除通识质量更新、通识清理、Q&A upsert/质量 API；MUST NOT 改坏 `feeding_intents`
- [x] 4.3 `main.py` 定时任务仅保留意图缓存清理；删除通识清理与启动 `build_vector_db` bootstrap

## 5. 语料、脚本与文档

- [x] 5.1 删除 `data/knowledge/**` 与 `scripts/build_vector_db.py`
- [x] 5.2 收缩 `README.md` / `docs/deploy-guide.md` / `docs/vector_db_guide.md`（或删除通识章节）中飞轮与通识构建说明；注明 Go 须停调已删 API
- [x] 5.3 收敛 `companion_session` 飞轮字段写入；grep 确认无残留 feedback/knowledge/qa 飞轮主路径

## 6. 意图缓存保护核对

- [x] 6.1 确认 `match_intent_cache` / 确认后 `intent_cache_store.add` / 定时清理 intents 仍可用
- [x] 6.2 手工或日志核对：意图路径不触碰已删通识/Q&A 集合
