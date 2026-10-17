## ADDED Requirements

### Requirement: Segment pinyin is cut once from the original

段解析 MUST 在任一维转换之前，把该段语音识别原文按字切成带调拼音，并在本次解析内复用。汉字 MUST 对应一个音节。数字、字母和标点 MUST 保留为空位，且空位 MUST NOT 参与词表比对。系统 MUST NOT 因句中夹有数字而放弃整句转换。

#### Scenario: Digits do not block a later event name

- **WHEN** 原文为「120毫升陪方奶」，且「陪方奶」与唯一事件词「配方奶」只差一个声调、声母和韵母相同
- **THEN** 事件视图 MUST 把该片段换成「配方奶」
- **AND** 「120」MUST 仍留在原文位置

### Requirement: Lexicon pinyin is cached outside the request path

非事件规则名词的拼音缓存 MUST 在该模块导入时建成。事件正式名与 `extra_names` 的拼音缓存 MUST 在事件字典载入和手动刷新时建成，并与字典缓存一起替换。转换时 MUST 只读这些缓存，MUST NOT 在请求路径上把词表重新转成拼音。未安装拼音库时，各维视图 MUST 等于原文。

#### Scenario: Dictionary refresh rebuilds the event cache

- **WHEN** 事件字典被手动刷新且词表发生变化
- **THEN** 事件拼音缓存 MUST 按新字典重建
- **AND** 其后的事件视图 MUST 使用新缓存

### Requirement: Rewrite allows one initial and requires a unique hit

转换 MUST 只使用调用方传入的词表。少于两个音节的词 MUST NOT 参加比对。系统 MUST 从左到右替换最长片段。带调拼音完全一致且只对应一个词时 MUST 替换为该词。否则仅当韵母和音节数相同，并且要么恰好一个音节的声母不同、要么恰好一个音节的声调不同，并且这样的词只有一个时，MUST 替换为该词。同一次替换 MUST NOT 既改声母又改声调。零个或多个候选时 MUST 保持该片段原文。声母与声调同时不同的片段 MUST 保持原文。

#### Scenario: One initial difference rewrites the event view

- **WHEN** 原文片段与唯一事件词只差一个声母，韵母和声调相同，且至少两个音节
- **THEN** 事件视图 MUST 使用该事件词

#### Scenario: One tone difference rewrites the event view

- **WHEN** 原文片段与唯一事件词只差一个音节的声调，声母和韵母相同，且至少两个音节
- **THEN** 事件视图 MUST 使用该事件词

#### Scenario: Tone and initial both differ

- **WHEN** 原文片段「是了」，词表中有「吃了」，二者声母和声调都不同
- **THEN** 该片段 MUST 保持「是了」

#### Scenario: Two candidates stay unchanged

- **WHEN** 同一片段在允许的声母差异或声调差异下对应两个词
- **THEN** 系统 MUST NOT 替换该片段

### Requirement: Pinyin rewrite result is logged

各维视图生成后 MUST 打一条 INFO 日志，包含维度名、结果（rewritten、unchanged、no_pinyin、unaligned 或 empty_lexicon）、原文片段和视图片段。改写成功时 `result` MUST 为 `rewritten`。

#### Scenario: A successful rewrite is logged

- **WHEN** 事件视图把原文中的一个片段换成了事件词
- **THEN** 日志 MUST 含 `dim=事件` 且 `result=rewritten`
- **AND** MUST 同时带上替换前片段和替换后片段

### Requirement: Each dimension view is built from the original

操作轨、事件、播报、定位和备注 MUST 各自用本维词表，对原文和只读拼音生成视图。某一维的替换 MUST NOT 写入其它维的视图，也 MUST NOT 改写原文。同一维的全部名词 MUST 在同一次最长匹配中使用。

#### Scenario: Event rewrite does not change the operation view

- **WHEN** 事件视图把「陪方奶」换成「配方奶」，操作轨词表不包含该片段
- **THEN** 操作轨视图 MUST 仍含原文「陪方奶」

#### Scenario: Longer rule noun is kept intact

- **WHEN** 操作轨词表同时含「吃了」和「吃了多少」，原文含「吃了多少」
- **THEN** 操作轨视图 MUST 保留整段「吃了多少」
- **AND** MUST NOT 先把前两字换成单独的「吃了」以致截断后半

### Requirement: Local rules read the dimension view

本维本地规则 MUST 读取本维视图。飞轮、小模型和对外复述 MUST 使用语音识别原文。十分钟对话 MUST 使用语音识别原文。

#### Scenario: Flywheel keeps the heard text

- **WHEN** 事件视图已把同音片段换成事件词，且该维本地规则未命中并继续走飞轮
- **THEN** 飞轮使用的段文本 MUST 仍是替换前的原文

### Requirement: Non-event rule nouns have a single source

操作轨、播报、定位和备注的规则名词 MUST 定义在同一个模块中。事件正式名与 `extra_names` MUST NOT 写入该模块。上述各维的本地匹配正则 MUST 由这些名词元组生成。向该模块增加一个不少于两个音节的名词后，MUST 同时进入该维拼音缓存和该维本地规则。

#### Scenario: A new rule noun participates in rewrite

- **WHEN** 规则名词模块为操作轨新增一个不少于两个音节的名词，且原文中有与它只差一个声母的片段，全表仅此一词
- **THEN** 操作轨视图 MUST 换成该名词
- **AND** 操作轨本地规则 MUST 能按该名词命中

### Requirement: Remark drops the event span by original offsets

备注判断 MUST 按事件维在原文上认定的起止位置删除该片段，MUST NOT 通过读取事件视图整句来删除。备注本维名词的剥离 MUST 使用备注视图。

#### Scenario: Misheard event name is removed by offset

- **WHEN** 事件维认定原文中「陪方奶」对应「配方奶」，备注原文在去掉该起止区间和备注名词后没有剩余明细
- **THEN** 备注 MUST 视为无剩余明细
- **AND** 备注路径 MUST NOT 依赖事件视图里已经写成的「配方奶」才能删掉这一段
