## Context

容器内 primary 与 DEEPSEEK_API_KEY、插件均正常，但 `~/.openclaw/agents/*/agent/models.json` 为空 `providers: {}` 时 chat 路径 Unknown model。

## Goals / Non-Goals

**Goals:** json5 显式 merge 登记 deepseek + flash，降低被空文件掏空的影响。  
**Non-Goals:** 本轮不写入口脚本清文件；不改 Go。

## Decisions

1. `models.mode: "merge"` + `providers.deepseek`（baseUrl、openai-completions、apiKey 引用 env、models 含 deepseek-v4-flash）。  
2. `agents.defaults.models["deepseek/deepseek-v4-flash"] = {}`。  
3. apiKey 用 `"$DEEPSEEK_API_KEY"`（与 compose 注入一致）；勿写明文。

## Risks / Trade-offs

- [schema 拒字段] → 若 Gateway 拒配，再收紧为文档允许的最小块。  
- [空 models.json 仍覆盖] → merge 进配置 providers 后通常仍可见；若否再加清文件 entrypoint。

## Migration Plan

改 json5 → `compose up -d --force-recreate`（不必 rebuild 镜像）。
