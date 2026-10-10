## ADDED Requirements

### Requirement: 段级 create 命中父事件须消歧
段多维事件维命中父事件且该段 `op` 为 create/update/delete（喂养落库类）时，系统 MUST 进入子事件消歧，MUST NOT 以父事件 id 直接落库。

#### Scenario: 换尿布段 create
- **WHEN** 段文本为「换尿布了」且事件维命中父事件「换尿布」，op 为 create
- **THEN** 系统 SHALL 返回尿尿/拉屎（或字典子事件）选项与澄清问句
- **AND** SHALL NOT 直接写入父事件历史行

### Requirement: 段级 read 命中父事件须展开叶子
段多维命中父事件且 `op` 为 read 时，系统 MUST 在确认查史后按既有规则展开子孙叶子拉史播报，MUST NOT 改为选叶子消歧。

#### Scenario: 今天换尿布几次
- **WHEN** 段为查史且事件为父「换尿布」
- **THEN** 系统 SHALL 查询其子孙叶子历史
- **AND** SHALL NOT 要求用户先选尿尿或拉屎才能查
