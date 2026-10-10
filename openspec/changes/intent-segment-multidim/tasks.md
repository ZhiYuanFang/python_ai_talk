## 1. Python：事件短说法库改造

- [x] 1.1 调整 `intent_cache_store`：document/metadata 语义改为短说法→事件（event_id/name/kind）；禁止整包 multi-events 免确认回放载荷
- [x] 1.2 命中日志打印查询文本与库内 document、score、event_id（阈值 0.72）
- [x] 1.3 确认/落库成功后仅按段写入短说法；复合整句不得单条写入
- [x] 1.4 提供/核对字典名与别名批量种子（admin bulk 或脚本）；文档说明 `CLEAR_FEEDING_INTENTS_ON_STARTUP` 清空后灌种再关开关

## 2. Python：段级多维与分句

- [x] 2.1 实现单事件判定与段级流水线 TYPE→EVENT→SHAPE→QTY→TIME（复用/搬迁现有 clock、quantity、history_mode 规则）
- [x] 2.2 实现分句 LLM（仅 segments + 可选句级 target_type；中文 reasoning；SSE 真流式）；提示落 `prompts/system.py`
- [x] 2.3 句级 history 优先；分句约束保留「几次/今天」等查史信号
- [x] 2.4 number 缺量追问；create 父消歧 / read 父展开接入段结果
- [x] 2.5 确认策略 C：阻塞项优先；短同质拼问（默认≤3）；长/混 op 逐段
- [x] 2.6 分句失败或段 TYPE/EVENT 失败 → 引导重说，禁止回退满血 classify

## 3. Python：意图图替换与删旧路径

- [x] 3.1 改造 `intent_graph` / `intent` 路由：主路径改为单事件多维 / 复合分句多维 → 拼装 → 既有确认/执行/查史
- [x] 3.2 删除或停用整包 `match_intent_cache` 免确认链与独立 `overlay_slots` 缓存后覆盖节点（逻辑并入段维）
- [x] 3.3 删除或停用满血一次多 events `classify_intent` 主路径与对应系统提示主契约
- [ ] 3.4 手工验收：串台反例、今天换尿布和喝奶几次、吃了120奶、换尿布消歧、缺量追问

## 4. Python：规则缺口收件箱

- [x] 4.1 实现缺口持久化（volume 文件库）与短窗去重；写入 TIME/TYPE/QTY/SHAPE miss 与事件 miss
- [x] 4.2 实现 `GET/PATCH`（或等价）`/v1/admin/rule-gaps`：分页新→旧、筛选、dismissed
- [x] 4.3 注册路由；缺口写入不得改事件向量库或热改规则代码

## 5. Go Hub（Python API 就绪后）

- [ ] 5.1 兄弟仓 Go：代理 Python `/v1/admin/rule-gaps`（列表/标已处理）
- [ ] 5.2 Hub 管理页：按维度/状态查看缺口原文（整句+段+reason+LLM 摘要），支持标已处理
- [ ] 5.3 与意图向量管理入口并列；文档说明「人工改 Python 规则发版，非热更新」
