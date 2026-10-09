## Why

查史成功后意图缓存仍把文档改写成「上一次{事件}是什么时候」，且命中后直接跳过 LLM。用户说「今天喝水几次」易向量近邻命中「上一次喝水…」类条目，串用错误的 `history_mode`/时间窗。关闭查史缓存会毁掉飞轮加速；仅按 mode 分文档也无法阻止 embedding 近邻串台。

## What Changes

- 意图缓存**命中接受前**增加廉价门闩：原文查史语义线索与 payload 的 `history_mode`（及必要的 ignore/窗线索）冲突时 MUST 视为未命中，回落分类 LLM。
- 同语义重复问（几次↔daily、上一次↔point）仍可命中并跳过 LLM，保留飞轮。
- `rewrite_standalone_document` 对 read：按 `history_mode` 区分文档文案（daily 不得再统一写成「上一次…什么时候」），减少自砸脚。
- 不关闭查史写入/检索缓存；不改 Go；不改播报「N次」文案（可另开）。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `intent-cache-flywheel`: 查史缓存命中须通过 history_mode 门闩；改写文档须区分 point/daily
- `intent-history-query`: 缓存串台不得用错误 mode 播报（几次不得被 point/上一次模板冒充）

## Impact

- **本仓**：`match_intent_cache`（或紧邻校验）、`rewrite_standalone_document`、可选与 classify 共用的线索正则。
- **飞轮**：冲突问法多付一次 LLM；真·重复仍秒回。
- **旧缓存**：门闩即可纠串台；改写仅影响新写入。
