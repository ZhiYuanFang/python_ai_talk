## 1. 命中门闩

- [x] 1.1 抽取或复用与 classify 对齐的 point/daily 原文强线索检测（中文注释说明仅用于缓存门闩）
- [x] 1.2 `match_intent_cache`：read/history 载荷在分数通过后做 mode 比对；冲突则当未命中并打日志

## 2. 写入改写

- [x] 2.1 `rewrite_standalone_document`：`history_mode=daily` 用区段/次数类文档句；point/缺省保持「上一次…什么时候」

## 3. 验收对照

- [x] 3.1 手工：先缓存「上一次喝水什么时候」，再问「今天喝水几次」→ 须走分类而非免确认点查（门闩单测语义已通；请本地点验）
- [x] 3.2 手工：连续两次「今天喝水几次」→ 第二次可命中 daily 缓存跳过分类（同 mode 不冲突；请本地点验）
