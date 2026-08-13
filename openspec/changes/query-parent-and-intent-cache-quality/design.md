## Context

意图查记录已在 `rebuild-intent-crud-agent` 收到 Python 图内：分类默认确认，确认后 `speak_history` 模板播报，高置信 `feeding_intents` 命中免确认。分类提示只注入叶子；`try_handle_pending` 只要解析到父 id 就改成选叶子消歧。点查模板不区分 `one|time|number`。意图缓存只有相似度 `0.72`，元数据无质量分，命中即执行并可能再次写入。`REBUILD_FEEDING_STANDARD_EVENTS` 在基线 `event-vector-dict-fields` 仍有规格，应用已不读，`.env.prod` 与部署文档仍残留。

约束：Python 为智能内核，经 HTTP 调兄弟仓；`feeding` 不得导入 `clinic`；中文注释；不写测试。

## Goals / Non-Goals

**Goals:**

- 查记录确认话术必带字典事件名。
- `read` 命中父：是/否确认 → 递归叶子 → 最近一条 → 点名父与叶。
- `create/update/delete` 命中父仍消歧。
- 点查模板按事件类型；计时无结束则报进行中；计数空/0 仍说数量为：0。
- 意图缓存：质量分 + 相似度双门槛；短窗重复同一问扣分并当未命中；定时清低分；查父缓存存父 id。
- 启动可选清空 `feeding_intents`；删除死配置 `REBUILD_FEEDING_STANDARD_EVENTS`。

**Non-Goals:**

- 不改日汇总压缩与相对时间格式。
- 不改 clinic/tip/care-alert 主路径。
- 不恢复 `feeding_events`。
- 不把「任意一天再说同一句」当成否决（那是飞轮正用）。
- 不生成测试文件。

## Decisions

### 1. 分类提示注入全量树，read 只输出父 id

- **选择**：`build_intent_classification_system_prompt` 使用 `event_dictionary_full`，每项带 `kind=parent|leaf` 与父/子名。规则：create/update/delete 禁用父 id；read 用户说父名则 `event_id`/`event_ids` 只含该父，禁止模型自行展开成叶子列表。
- **原因**：自行展开会与「分别点查」撞车；执行层靠「原始 id 是父」决定塌成最近一条。
- **备选否决**：只在执行层做父名子串检测 — 分类仍看不见父，容易把「换尿布」打进 missing 或乱点叶子。

### 2. 查父确认是是/否，确认后按 op 切开

- **选择**：查父与查叶子一样 `need_confirm=true`（缓存高置信除外）。话术：`请确认是否查询「{事件名}」的历史？` 由 Python 用字典名覆盖 LLM 空/泛称。用户确认后：`op=read` 且为父 → `get_descendant_leaves`（递归）→ `speak_history`；`create/update/delete` 且为父 → 仍 `parent_disambiguation`。
- **原因**：首轮免确认会让错分类在 `speak_history` 写入飞轮。现有 `try_handle_pending` 对任何父都消歧，会把「确认查换尿布」变成选尿尿/拉屎，必须按 `pending.op` 分支。
- **备选否决**：查父免确认 — 飞轮污染。

### 3. 点查模板按字典 event_type

相对时间继续 `format_history_time`。类型优先字典 `event_type`，历史行缺则按 id 回查。

| 类型 | 叶子点查 | 父点查（赢的叶子） |
|---|---|---|
| one | 上一次{叶}是{相对时间}。 | 上一次{父}的时候是{叶}，{相对时间}。 |
| time 已结束 | 上一次{叶}是{相对时间}，用时X小时Y分。 | 上一次{父}的时候是{叶}，{相对时间}，用时…。 |
| time 无 endTime | 上一次{叶}是{相对时间}开始的，现在正在进行中。 | 同样包父名 |
| number | 上一次{叶}是{相对时间}，数量为：{n}。空当 0 | 同样包父名 |

无任何叶子记录：`没有记到{父或叶}相关记录。` 「分别」多叶子仍各报一条，不塌。日汇总不改。

### 4. 意图缓存质量分与短窗重复

- **双门槛**：相似度 `>= 0.72`（现状）且 `quality_score >= 0.7`（缺省按 0.8）才命中。质量分存在 Chroma **顶层 metadata**，不塞进 payload JSON。
- **短窗纠错**：按 `device_no` 记 `last_cache_turn{text, vector_id, ts}`，TTL **3 分钟**。缓存免确认执行后，同一设备短窗内同一问（去标点后相等）再来 → 对该 **命中 id** `quality_score -= 0.2`（下限 0），当未命中，走探针/分类/确认。隔天再说同一句：窗口过期，正常命中。
- **写入**：仍仅确认后成功拉史或落库；默认 `quality_score=0.8`。同一 `document` 已存在则更新该条而非新 uuid（避免分身绕开扣分）。正确再确认后写/更新新条，不给被扣分旧条自动加分。
- **定时清理**：与知识库同一 24h 循环，只扫 `feeding_intents`，`quality_score < 0.3` 删除；不得动 `mother_baby_knowledge`。
- **查父载荷**：`event_id`/`event_name`/`event_ids` 存父，命中后再展开。
- **备选否决**：任意重复同一句都 miss — 飞轮永不生效。

### 5. 启动清库与删除死配置

- **选择**：`CLEAR_FEEDING_INTENTS_ON_STARTUP` 默认 `false`。为 true 时预热只 `delete_collection("feeding_intents")` 再创建空集合。用完改回 false。三层同名：`.env*`、`docker-compose.yml`、`settings.py`。
- **删除**：代码/环境文件/部署文档中的 `REBUILD_FEEDING_STANDARD_EVENTS`（基线 `ENV-gated one-shot standard rebuild` 一并移除）。
- **备选否决**：只改 `.env.prod` — 应用读不到。

## Risks / Trade-offs

- [分类仍吐叶子 id] → 提示写死「用户说父名则输出父」；执行层若原文含父名可再校正（实现时可做轻量兜底，不得替代提示词）。
- [短窗内用户只是没听清又问一遍] → 第二次要再确认一次；用一次确认换错缓存不连打两枪。
- [同 document 多历史分身] → 写入改为按 document 更新；清理扫低分。
- [生产误开清库] → 默认 false；日志明确「已清空 feeding_intents」；文档强调改回。

## Migration Plan

1. 部署含本变更的镜像；`CLEAR_FEEDING_INTENTS_ON_STARTUP` 保持 false，除非要丢掉测脏缓存。
2. 旧 `feeding_intents` 条目无 `quality_score` 时按 0.8。
3. 回滚：回退镜像即可；质量分元数据对旧代码可忽略。

## Open Questions

无。短窗 3 分钟、质量下限 0.7、清理线 0.3、扣 0.2 按探索默认落地。
