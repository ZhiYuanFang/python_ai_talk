## Why

喂养失败后的软回复把宝宝画像收成了 `sex=0`，模型不知道这是女，也看不到名字和月龄。诊疗回答里的性别读的是 `gender`，而生日接口只有 `sex`，所以那一行一直是「未知」。

## What Changes

- 画像提示与 Go 生日接口对齐：`babyName`、`birthday`（Unix 秒，`0` 表示未设置）、`sex`（`0` 女，`1` 男）。
- 诊疗回答的性别改为读 `sex` 并写成女或男；其它值写未知。月龄仍由 `birthday` 计算，无法计算时写未知。有名字时增加名字一行。
- 覆盖缺口软回复用同一套说法注入宝宝基础信息，不再输出 `sex=0` 这类原始键值。预测算法快照仍只附已有缓存，没有则不重算。

## Capabilities

### New Capabilities

- `baby-profile-prompt-fields`: 诊疗与失败软回复按 `babyName`、`birthday`、`sex` 向模型说明宝宝名字、月龄和性别。

### Modified Capabilities

- （无基线独立 spec 名需整段替换；行为以本 change 的新增 capability 为准。）

## Impact

- 诊疗回答的用户消息（clinic）
- 喂养覆盖缺口软回复的画像摘取
- 不改生日接口，不改月龄计算公式，不改预测快照的缓存策略
