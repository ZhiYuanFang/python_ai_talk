## Context

仓库并存多条「飞轮」：care_alert 全局 prompt 对比样例、clinic 隐式采纳 → 通识质量分、Q&A 捷径 promote/demote、以及喂养 `feeding_intents` 意图缓存。前三者收益弱或写路径已半死（care_alert feedback 已注释），却占用图节点、会话字段、Chroma 集合与部署卷。产品决定只保留意图缓存飞轮，并删除通识检索注入与相关 API/语料。

## Goals / Non-Goals

**Goals:**

- 运行时仅保留意图缓存闭环；clinic/tip/care_alert 不再依赖通识或 Q&A。
- 删除 BREAKING 端点与死代码，降低维护面。
- 用 OpenSpec 退役基线中对应 capability 要求。

**Non-Goals:**

- 不改写意图分类/CRUD 业务规则（除确保缓存读写完好）。
- 不改 growth_trajectory。
- 不在本仓修改 Go/Flutter（仅文档/Impact 要求停调）。
- 不迁移历史 `mother_baby_knowledge` / `qa_fast_path` 数据（可废弃留盘或随卷清理，不设迁移义务）。

## Decisions

1. **整路由删除，不留 410 空壳**  
   - `POST /v1/care-alert/feedback`、`/v1/knowledge/*` 从 FastAPI 卸载。  
   - 备选：保留 ACK 兼容 —— 否决（Flutter 已无业务线；空壳仍增代码）。

2. **clinic 去掉 `implicit_feedback` 整节点**  
   - 去 Q&A/通识后无副作用；入口改为现隐式之后的下一跳（如 `fetch_baby_profile`）。  
   - 删除或掏空 `suggestion_acceptance` 飞轮 API，避免残留调用。

3. **care_alert 保留静态 prompt 加载**  
   - 继续可用 `prompt_store` + `prompt.json` 的 `output_format`；删除 `contrastive_examples` 飞轮写路径、`flywheel_store`、ledger、`prompt_flywheel`。  
   - 备选：全部内联硬编码 —— 可选后续；本变更优先删飞轮、保留文件加载以少动 analyze。

4. **通识语料与 `build_vector_db` 从仓库删除**  
   - 去掉 `data/knowledge/**`、`scripts/build_vector_db.py`、`main` 空库 bootstrap。  
   - 定时任务只保留意图缓存清理，MUST NOT 再扫 `mother_baby_knowledge`。

5. **删除顺序**  
   - care_alert 飞轮与 feedback → clinic Q&A + implicit → clinic/tip `search_vectors` 与 prompt → knowledge API/vector 通识与 Q&A helpers → 语料/脚本/文档/settings。  
   - 全程用 grep 保护 `intent_cache_store` / `feeding_intents`。

6. **companion_session**  
   - 收缩或停止写入 `knowledge_ids` / `qa_match_id` / `feedback_applied` 等飞轮字段；保留多轮对话文本能力。

## Risks / Trade-offs

- [Go 仍调用已删 API → 404] → Impact 标明 BREAKING；部署清单含兄弟仓停调。  
- [陪伴答失去本地百科接地] → 已接受；依赖 system/史/LLM。  
- [误删意图缓存清理] → tasks 含显式核对 `main.py` 只清 intents。  
- [基线 capability 多、delta 面大] → 以 REMOVED + 新 ADDED 边界需求为主，收版时合并进版本基线。

## Migration Plan

1. 合并本变更并发布 Python 镜像。  
2. 同步 Go：删除对 `/v1/care-alert/feedback`、`/v1/knowledge/*` 的内调。  
3. 可选：清理 chroma 中废弃 collection（运维手工，非代码必须）。  
4. 回滚：恢复本变更前镜像与路由；语料需从 git 历史取回。

## Open Questions

- 无（explore 已确认：API 删除、无 implicit、语料/脚本删除）。
