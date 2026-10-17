## Why

「还是拉屎了。」剥掉事件名之后还剩「还是」，备注判断把它当成明细，于是空转一次备注模型，并记下缺口、写入空备注飞轮。口头垫词、「孩子」「宝宝」和孩子昵称都不是备注明细。

## What Changes

- 备注是否还有明细之前，先剥掉一组废话词：还是、就是、然后、那个、这个、其实、反正，以及称呼「孩子」「宝宝」。
- 这些词写在规则名词模块的备注一组里，同时参与备注视图的近音转换和明细剥离。
- 孩子昵称不写进该文件。备注判断前用本段 `device_no` 读取宝宝画像的 `babyName`，字面剥掉。一个字的昵称也剥。画像没有名字或请求失败时，仍剥固定废话和称呼。
- 剥完没有剩余文字时，备注为空，不查备注飞轮、不调备注模型、不记备注缺口。
- 剥完仍有描述（如「有点凉」）时，保持现有飞轮再到模型的路径。

## Capabilities

### New Capabilities

- `remark-filler-strip`: 备注判断前剥掉废话、孩子称呼和当次画像昵称

### Modified Capabilities

- 无。基线 `openspec/specs/v0.0.1.md` 没有「剥完套话后是否还有备注」的既有需求。未收版的备注无明细短路仍适用：本变更只扩大被当成套话的词。

## Impact

- `app/feeding/services/dim_rule_lexicon.py`：新增备注废话与称呼元组，并入备注视图词表。
- `app/feeding/services/segment_remark.py`：明细判断增加这组剥离，并接受当次昵称。
- `app/feeding/services/segment_multidim.py`：备注判断前读取 `babyName`。
- 画像接口仍是现有 `get_baby_profile`。无对外 API 字段变更。
