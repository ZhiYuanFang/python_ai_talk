## Context

Go `OpenClawHTTPClient` 设置 `x-openclaw-model: provider/name`；Python 门禁当前原样转发。OpenClaw 用该头覆盖默认模。探索结论：只写 `agents.defaults.model.primary` 无法保证「Go 传入没用」；须在门禁剥离该头，并在 json5 钉死 flash。

## Goals / Non-Goals

**Goals:**

- 经门禁进入的 Intent/Clinic/Care 请求，实际 LLM 为 `deepseek/deepseek-v4-flash`。
- Go 继续可发送 `x-openclaw-model`，但对 Gateway **无效**。
- README 写清约定，避免运维仍以为 Go 注模生效。

**Non-Goals:**

- 修改 Go 选模 / 停发头 / 额度语义对齐（后续另案）。
- 解决 deepseek provider 未注册导致的 Unknown model（若仍存在，运维用 models set / 插件；本变更假定 env 已有 `DEEPSEEK_API_KEY`）。
- 改 Python tools 隐式采纳所用模型。

## Decisions

1. **门禁剥离 `x-openclaw-model`**  
   - 理由：不改 Go 即可让注入无效；比 allowlist 拒掉非 flash 更符合「一律 flash」。  
   - 仍透传：`x-openclaw-session-key`、`x-pangbao-api-token`。

2. **json5 `agents.defaults.model.primary = "deepseek/deepseek-v4-flash"`**  
   - 无 override 头时 Gateway 用此主模。  
   - 可选：三个 `list[]` 条目各写相同 `model`（防御性）；优先 defaults 一处，避免 schema 不认字段时启动失败——实现时若 doctor/validate 报错再收敛为仅 defaults。

3. **`body.model` 仍为 `openclaw/intent|clinic|care_alert`**  
   - 继续选 agent，与 LLM 解耦。

4. **README**  
   - 架构/OpenClaw 节注明：LLM 写死 flash；Go 头被门禁忽略；恢复 Go 注模需恢复透传。

## Risks / Trade-offs

- [额度与实模脱节] → README/提案标明临时策略；日后改 Go。  
- [Unknown model 仍在] → 与剥头无关；需 DeepSeek auth + 目录；验收时若失败另开运维/change。  
- [直打 :18789 仍可带头 override] → 产品约定对外只走门禁；勿裸放 18789。

## Migration Plan

1. 改 gate + json5 + README → 重启 OpenClaw（volume 挂载 json5）与 Python。  
2. 回滚：恢复透传头；去掉或改回 primary。

## Open Questions

- 无。
