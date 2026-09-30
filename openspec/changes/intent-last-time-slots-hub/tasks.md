## 1. 点查「上次」语义（Python）

- [x] 1.1 在 `speak_history` 选行逻辑中跳过无有效 endTime 的进行中记录，优先取已完成
- [x] 1.2 实现「仅有进行中」固定话术：目前仅找到一条记录，是{相对时间}发生，正在进行中
- [x] 1.3 父事件展开后的「最近一条」同样应用跳过进行中规则与仅进行中话术

## 2. 槽位覆盖（Python）

- [x] 2.1 新增/强化 clock 抽取工具（Asia/Shanghai；避开与 qty 冲突）
- [x] 2.2 强化 quantity 抽取：优先毫升/ml/吃了上下文，避免把「X点」当数量
- [x] 2.3 实现 `overlay_slots` 节点：覆盖 quantity/start_time；多钟点且 events 长度=1 时降级
- [x] 2.4 将 `overlay_slots` 接入 `intent_graph`（命中后先覆盖；降级则走 classify）
- [x] 2.5 写缓存/admin 写入时剥离 create 骨架中的绝对 start_time

## 3. 同叶多时刻 create（Python）

- [x] 3.1 更新 classify system 提示：create 可填 start_time；一句 N 次→N 条 events；允许同 event_id
- [x] 3.2 更新多事件确认文案生成，带上各条时间与数量
- [x] 3.3 核对 `collect_event_items` / batch 对同 event_id 多 create + 各 start_time 的传递

## 4. 意图向量管理 API（Python）

- [x] 4.1 `intent_cache_store` 增加 list（分页或全量）、delete_by_id、bulk_upsert
- [x] 4.2 新增管理路由（list / bulk / delete），中文注释；不写 MySQL
- [x] 4.3 与现有鉴权/内网约定对齐（供 Go voice admin 调用）

## 5. 兄弟仓 go_ai_talk（Hub）

- [x] 5.1 扩展 `PythonAIClient`：意图向量 list/bulk/delete
- [x] 5.2 voice-service 增加 `/voice/admin/api/intent-vectors/*` 代理上述接口
- [x] 5.3 新增 `intent-vector-admin.html`：列表、批量上传、删除
- [x] 5.4 `admin-modules.js` + `admin_static_pages.go` 挂载 Hub 入口

## 6. 手工验收

- [ ] 6.1 验收：有完成+进行中时「上次」答完成记录；仅进行中时新话术
- [ ] 6.2 验收：种子「记录吃了120毫升配方奶」+「记录5点吃了120毫升配方奶」落到 5 点
- [ ] 6.3 验收：三钟点一句对单条种子强制走 LLM/确认而非免确认错写
- [ ] 6.4 验收：三时刻喂养句分类为 3 条 events，确认文案含量时，batch 三条
- [ ] 6.5 验收：Hub 可列表、上传种子、删除错误向量且删除后不再命中
