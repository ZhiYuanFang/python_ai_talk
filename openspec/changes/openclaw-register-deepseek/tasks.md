## 1. json5

- [x] 1.1 在 `openclaw.json5` 增加 `models.mode=merge` 与 `providers.deepseek`（含 deepseek-v4-flash；apiKey 引用 env）
- [x] 1.2 `agents.defaults.models` 登记 `deepseek/deepseek-v4-flash`

## 2. README

- [x] 2.1 注明显式登记 DeepSeek；改 json5 后 recreate

## 3. 校验

- [x] 3.1 `openspec validate openclaw-register-deepseek --strict`
