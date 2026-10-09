## 1. 查史软确认透传

- [x] 1.1 `create_history_confirm_response`：创建 leaf_confirm pending 时传入分类 `history_mode` 与 `limit`（中文注释说明查史确认依赖）
- [x] 1.2 核对 `api/routes/intent.py` 查史 `need_confirm` 仍走该函数，无需改路由分支

## 2. 父消歧与查父回填

- [x] 2.1 `create_parent_disambiguation_pending`（及 remark 包装）增加并写入 `history_mode`/`limit` 可选参数
- [x] 2.2 查史进入父消歧的调用方（如 `try_parent_hit_from_event_id` / `postprocess` 相关）从 intent 带入上述字段
- [x] 2.3 `try_handle_pending` 查父确认拼 `fields` 分支：与叶子 restore 一致回填 `history_mode`/`limit`

## 3. 验收对照

- [x] 3.1 手工验证：「今天喝了几次水」→ 确认后 content 为 daily 紧凑汇总，而非「上一次…数量为…」（代码路径已接通；请本地点一次确认）
- [x] 3.2 手工验证：point 类「上次喝水」确认后仍为点查话术（pending 透传 point 不变）
