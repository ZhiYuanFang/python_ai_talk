## Context

`compound-switch-and-dict-event-type` 已用提示教复合句拆 `events[]`、同音表，并禁止注入进行中。本地 `looks_like_history_query` 见「上一次」就当查询。两边叠加后，「删除上一次坐练习」会变成查记录；同音只能继续加词对。

约束：经 HTTP 调兄弟仓；`feeding` 不得导入 `clinic`；中文注释；不写测试。结束计时仍不由 Python 填 `history_id`。

## Goals / Non-Goals

**Goals:**

- 分类提示只解释字段与事件表，不用用户话术关键字判 `op`。
- 删除本地查询句正则；备注探针仅 OOV 时请求。
- 分类前注入进行中计时摘要，帮助同音/停止对准字典叶子。
- 查记录确认只看 `op=read`。

**Non-Goals:**

- 不改 Go end-latest、filter 契约。
- 不改非计时 `endTime=startTime`、batch 先 end。
- 不把进行中行的 `history_id` 交给模型或写入 end 项。
- 不生成测试文件。

## Decisions

### 1. 提示改为字段定义，去掉话术表

- **选择**：系统提示包含：角色一句、当前时间、事件简表、可选备注/进行中数据、`op`/`action`/`events[]` 等字段含义、表约束（只用表内 id、CUD 仅叶子、read 父名只填父 id、不返回 `event_type`、只出 JSON）。不写「上次/什么时候/不 X 了/怕≈爬」。
- **原因**：关键字规则会套娃；删 vs 查应由 `delete`/`read` 的含义区分。
- **备选否决**：继续为「删除上一次」加例外句式。

### 2. 删除 `looks_like_history_query`

- **选择**：删除该函数与 `query_utterance.py`（若无其它引用）。`match_intent_cache` 去掉「查询句命中 create 则丢」。`remark_probe` 不再用该函数门控；抽出字典外词才打 filter。
- **原因**：本地猜查询句会误伤删除/结束。
- **风险**：查询句可能命中 create 缓存并免确认。接受；分类默认确认仍覆盖缓存未命中路径。不另加正则闸。

### 3. 进行中探针：数据锚，不是关键字

- **选择**：缓存未命中时，近窗拉一小页历史，Python 保留 `endTime` 空或 0 且字典 `event_type=time` 的叶子，压成一行：名称、字典 id、开始时间。无则写「当前无进行中计时」。注入分类提示。不写 `history_id`。
- **落点**：与备注探针同一节点，避免改图结构。
- **原因**：同音对整本字典易错，对短名单更稳。
- **备选否决**：为 end 项填 history_id — 与 Go end-latest 重复。

### 4. 确认只认 `op`

- **选择**：`create_leaf_confirm_pending` 仅 `op=read` 使用查记录话术。`action=search` 且 `op=delete|update|create` 不得改写成「是否查询历史」。删除确认点出事件名与删除。
- **原因**：JSON 的 `action` 无 delete，模型常给 search，会把删除说成查询。

## Risks / Trade-offs

- [复合句不再用句式教] → 靠 `events[]` 字段含义；确认句点出结束/开始供用户否决。
- [查询句误套 create 缓存] → 短窗重复扣分；首次误套需用户从结果发现。不恢复正则。
- [进行中误判（非计时 endTime=0 脏数据）] → 只收字典 `type=time`。
- [filter 无进行中参数] → 近窗小 limit + 客户端过滤。

## Migration Plan

1. 只发 Python 镜像。
2. 回滚：回退镜像；提示恢复关键字；无进行中注入。

## Open Questions

- （无。缓存误套 create 按 Decision 2 接受。）
