## Why

意图各维大多靠飞轮或小模型才接得住第一句，ASR 同音错字又会让事件名对不上。规则没覆盖的说法只在时间和数量上进入缺口列表，运维补规则时看不见其它维。

## What Changes

- 段解析前，用事件字典的正式名与 `extra_names` 做同音替换。整句里某个音只对应一个事件词才替换；对上多个或对不上则保持原文。解析用替换后的句子，对外复述与十分钟对话仍用 ASR 原文。
- 各维在飞轮之前加本地规则。命中即停，不再查飞轮、不调该维小模型。规则宁可不中，也不把「吃了多少」和「要吃多少」判成同一轨。
- 本地规则未命中时写入规则缺口，飞轮接住也记。`reason` 区分飞轮命中与小模型。形状维不单记。
- **BREAKING**（对 Hub 列表）：`GET /admin/rule-gaps` 在未指定 `dimension` 时返回全部 open 缺口，不再只合并 `time` 与 `quantity`。
- 先改本仓 Python，再改兄弟仓 Go Hub：规则缺口列表按维度展示与筛选，不再只做时间、数量两块。

## Capabilities

### New Capabilities

- `intent-homophone-normalize`: 解析前按事件集做唯一同音替换
- `intent-dim-local-rules`: 各维本地规则先于飞轮与小模型
- `intent-rule-gap-all-dims`: 规则未覆盖统一记缺口，列表与 Hub 展示全部分维

### Modified Capabilities

- （无）当前基线 `openspec/specs/v0.0.1.md` 未收录这些维的规则顺序与缺口列表范围。

## Impact

- `app/feeding/services/segment_multidim.py`、`dim_resolve.py`、事件匹配与各维飞轮入口
- 新增同音索引（事件字典刷新时重建）；需要拼音能力，仓库内目前没有
- `app/feeding/services/rule_gap_store.py`、`app/api/routes/rule_gaps_admin.py`
- 兄弟仓 Go Hub 的规则缺口页（本仓不含该前端；Python 列表契约先定，再改 Go）
