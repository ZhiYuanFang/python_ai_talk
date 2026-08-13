## 1. 去掉本地查询句判断

- [x] 1.1 删除 `looks_like_history_query` 及 `query_utterance.py`（确认无其它引用）
- [x] 1.2 `match_intent_cache` 去掉「查询句命中 create 则忽略」
- [x] 1.3 `remark_probe` 改为抽出字典外词才打 filter，不再用查询句正则门控

## 2. 进行中探针

- [x] 2.1 缓存未命中时近窗拉史，筛 `endTime` 空/0 且字典 `type=time` 的叶子，压成名称+字典 id+开始时间；无则明确无进行中；不含 history_id
- [x] 2.2 将该摘要注入分类提示（可与备注探针同一节点）

## 3. 分类提示与确认

- [x] 3.1 重写分类系统提示：字段含义 + 表约束 + 当前时间/事件表/探针数据；删除「上一次=read」、同音表、句式模板
- [x] 3.2 查记录确认仅当 `op=read`；`op=delete` 即使 `action=search` 也说删除；补中文注释

## 4. 校验

- [x] 4.1 运行 `openspec validate schema-classify-and-in-progress-probe --strict` 并修复规格问题
- [x] 4.2 对照规格手工核对：提示无上一次即查询、删除上一次为 delete、有进行中则注入且无 history_id、备注探针不靠查询正则
