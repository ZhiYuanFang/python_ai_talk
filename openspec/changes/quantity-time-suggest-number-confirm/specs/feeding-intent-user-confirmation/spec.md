## ADDED Requirements

### Requirement: 冲突改选场景优先保留分类确认问句
当分类产出非空 `confirm_message`，且叶子确认 pending 因「计量语义改选近义 number 叶」或普通记录确认而创建时，系统 MUST 将该 `confirm_message` 作为用户可见确认话术（`clarify_message` / 对外 confirm_message）。仅当 `confirm_message` 为空或缺失时，系统 MAY 使用模板生成的叶子确认问句。系统 MUST NOT 在冲突改选场景用模板无条件覆盖已有的简洁 LLM 问句。

#### Scenario: 瓶喂建议问句不被模板盖掉
- **WHEN** 分类将带 quantity 的 create 改选为计量叶「瓶喂母乳」
- **AND** `confirm_message` 为简洁问句（如「您是要记录瓶喂母乳60毫升嘛？」）
- **AND** 系统创建 leaf_confirm pending
- **THEN** 用户可见确认话术 SHALL 为该 `confirm_message`（或语义等价保留）
- **AND** MUST NOT 替换成仅针对计时「母乳」的模板问句

#### Scenario: 无分类问句时回退模板
- **WHEN** 叶子确认需要话术但 `confirm_message` 为空
- **THEN** 系统 SHALL 使用既有模板生成确认问句（如「您是要…吗？」）
