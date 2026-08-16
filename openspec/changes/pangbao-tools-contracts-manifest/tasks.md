## 1. Manifest

- [x] 1.1 更新 `openclaw.plugin.json`：增加 `contracts.tools` 显式工具名数组（与现有顶层 `tools` / 源码 `name` 对齐）；禁止 `true`/通配
- [x] 1.2 确认顶层 `tools` 保留或按 design 注明；名称列表与 `src/index.ts` 一致

## 2. 文档

- [x] 2.1 更新 `deploy/openclaw/plugins/README.md`（及必要时根 README）：`contracts.tools` 要求与 restart 说明
- [x] 2.2 自检说明：restart 后 intent chat 不再出现 `No callable tools remain` / `no registered tools matched`
