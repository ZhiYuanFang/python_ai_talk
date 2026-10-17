## ADDED Requirements

### Requirement: Remark detail check strips filler and child references

备注是否还有明细时，系统 MUST 在剥掉事件片段、钟点、数量、时段词和记一笔套话之后，再剥掉备注废话词。废话词 MUST 至少包含：还是、就是、然后、那个、这个、其实、反正、孩子、宝宝。这些词 MUST 定义在非事件规则名词模块中，并参与备注视图的近音转换。剥完没有剩余文字时，系统 MUST 将备注视为空，且 MUST NOT 查备注飞轮、MUST NOT 调用备注模型、MUST NOT 记备注缺口。

#### Scenario: Filler alone does not call the remark model

- **WHEN** 段原文为「还是拉屎了。」，事件名是「拉屎」，剥掉事件名、套话和「还是」后没有剩余文字
- **THEN** 备注 MUST 为空
- **AND** 系统 MUST NOT 调用备注模型

#### Scenario: Real detail still reaches the remark path

- **WHEN** 段原文在剥掉废话词之后仍含「有点凉」
- **THEN** 系统 MUST 继续现有备注飞轮与模型路径

### Requirement: Baby nickname is stripped for the current device

备注明细判断 MUST 用本段 `device_no` 读取宝宝画像中的 `babyName`，并在同一轮剥离中字面删除该昵称。一个字的昵称也 MUST 删除。画像没有 `babyName` 或读取失败时，系统 MUST 仍剥离固定废话词和「孩子」「宝宝」，且 MUST NOT 因此失败整段解析。昵称 MUST NOT 写入规则名词模块。

#### Scenario: Nickname is removed before the empty check

- **WHEN** 当前设备画像的 `babyName` 为「豆豆」，段原文剥掉事件名后只剩「还是豆豆」
- **THEN** 备注 MUST 为空
- **AND** 系统 MUST NOT 调用备注模型

#### Scenario: Missing profile still strips static child words

- **WHEN** 宝宝画像读取失败，段原文剥掉事件名后只剩「宝宝」
- **THEN** 备注 MUST 为空
- **AND** 系统 MUST NOT 调用备注模型
