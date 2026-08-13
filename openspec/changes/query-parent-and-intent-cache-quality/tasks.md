## 1. 层级与分类提示

- [x] 1.1 在 `event_hierarchy.py` 增加递归 `get_descendant_leaves`（中文注释），多层父一律收到真正叶子
- [x] 1.2 分类提示改为注入全量树，标明 parent/leaf 与从属；规则：CUD 禁用父 id，read 用户说父名只输出父 id
- [x] 1.3 `classify_intent` 使用 `event_dictionary_full` 构建提示，并在匹配 id 时能解析父事件

## 2. 查记录确认与 pending

- [x] 2.1 Python 生成查记录 `confirm_message`，必带字典事件名；禁止「该事件」兜底；有 id 无名则回查字典
- [x] 2.2 `try_handle_pending`：`op=read` 且目标为父时确认后展开叶子拉史，不得改 `parent_disambiguation`；CUD 命中父仍消歧
- [x] 2.3 流式与非流式 HISTORY 确认共用同一套点名话术（含 `intent.py` 原兜底句）

## 3. 点查模板与父展开

- [x] 3.1 `speak_history`：event_ids 含父则递归展开叶子再 filter；来自父则塌成 `startTime` 最近一条并点出父名与叶子名；「分别」多叶子仍各报
- [x] 3.2 点查模板按 `one|time|number`：一次性不带数量；计时用时（时分）；无 endTime 说开始相对时间且正在进行中；计数「数量为：」空当 0
- [x] 3.3 查父成功写入缓存时载荷存父 id/名，不存展开后的叶子 id 列表；日汇总路径不改

## 4. 意图缓存质量分与清理

- [x] 4.1 `intent_cache_store` 顶层 metadata 增加 `quality_score`（默认 0.8）；同一 document 更新而非新 uuid；检索同时要求相似度≥0.72 且质量分≥0.7
- [x] 4.2 按 `device_no` 记录短窗（3 分钟）上次缓存免确认执行；窗内同一问再来对该条扣 0.2 并当未命中，走分类确认
- [x] 4.3 与知识库同一 24h 循环清理 `feeding_intents` 中质量分低于 0.3 的条目，不得动 `mother_baby_knowledge`

## 5. 环境变量与文档

- [x] 5.1 `settings.py`、`.env.example`、`env/.env.prod`、`docker-compose.yml` 增加 `CLEAR_FEEDING_INTENTS_ON_STARTUP`（默认 false）；预热为 true 时只清空 `feeding_intents`
- [x] 5.2 删除 `REBUILD_FEEDING_STANDARD_EVENTS`（环境文件、settings 若有、`docs/deploy-guide.md`）；补上新变量说明
- [x] 5.3 所有新增/改动业务代码补全中文注释

## 6. 校验

- [x] 6.1 运行 `openspec validate query-parent-and-intent-cache-quality --strict` 并修复规格问题
- [x] 6.2 对照规格手工核对：查记录确认点名、查父确认后展开最近一条、记父仍消歧、三类模板、短窗重复扣分、清库开关默认关
