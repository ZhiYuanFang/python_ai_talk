## Context

`LLMClient._get_client` 仅当 `provider == "glm"` 时使用 `settings.glm_api_key` / `glm_base_url`（智谱开放平台）。调用方（如 go_ai_talk）传入 `zhipu`，触发 `ValueError`。配置与密钥已就绪，缺口只在名称映射。

## Goals / Non-Goals

**Goals:**

- `zhipu` 与 `glm`（大小写不敏感）走同一智谱客户端路径
- 客户端缓存 key 使用规范化后的 provider，避免重复实例
- 文档/schema 描述与行为一致

**Non-Goals:**

- 重命名环境变量为 `ZHIPU_*`
- 修改 Go 强制只传 `glm`
- 新增其它厂商别名（除非后续单独立项）

## Decisions

### 1. 规范化点放在 `_get_client`

- **选择**：入口对 `provider` 做 `strip().lower()`，再将 `zhipu` → 内部规范名 `glm`
- **理由**：`invoke` / `stream` / 隐式飞轮等所有路径都经 `_get_client`，一处修复全覆盖
- **备选**：仅在路由层改写（易漏 suggestion_acceptance 等）

### 2. 缓存 key 用规范名

- **选择**：`cache_key = f"{canonical}:{model_name}"`（canonical 为 `glm` 或 `deepseek`）
- **理由**：`zhipu:glm-4` 与 `glm:glm-4` 共享同一 `ChatOpenAI` 实例

### 3. 权威内部名保持 `glm`

- **选择**：配置与日志内部仍可用 `glm`；对外双收
- **理由**：与现有 `GLM_API_KEY` 一致，改动面最小

## Risks / Trade-offs

- [未知大小写变体] → `lower()` 覆盖 `Zhipu` / `ZHIPU`
- [其它拼写如 `zhipu`] → 仍报不支持；不扩大模糊匹配
- [日志仍显示请求原始 provider] → 可在 `_get_client` 内用规范名打日志；请求 payload 日志可保留原始值便于对账

## Migration Plan

1. 部署含别名逻辑的版本后，`provider=zhipu` 立即可用
2. 回滚：恢复仅认 `glm`（调用方需改回或继续失败）

## Open Questions

- 无（产品已选定双收）
