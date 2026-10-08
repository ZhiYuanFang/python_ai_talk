## ADDED Requirements

### Requirement: 计时闭合补记按时长与钟点填写起止
当用户对计时类叶子（字典 `event_type=time`）表达已发生的一段时长或起止时刻时，系统 SHALL 生成 create 且 `start_time` 与 `end_time` 均大于 0（闭合区间），MUST NOT 将该类补记落成 `end_time=0` 的进行中开表。时长字段 MUST NOT 误写入 `quantity`/`eventNumber`（除非用户同时给出可计量的毫升等数量语义）。

#### Scenario: 有钟点加时长
- **WHEN** 用户说「早上8点母乳10分钟」且事件为计时叶子母乳
- **THEN** 落库 startTime SHALL 为当日（Asia/Shanghai）08:00
- **AND** endTime SHALL 为 08:10
- **AND** endTime MUST NOT 为 0

#### Scenario: 无钟点仅时长
- **WHEN** 用户说「母乳10分钟」且无钟点词
- **THEN** endTime SHALL 约为当前时刻
- **AND** startTime SHALL 约为当前时刻减去 10 分钟
- **AND** endTime MUST NOT 为 0

#### Scenario: 双钟点起止
- **WHEN** 用户说「8点到8点半母乳」（或等价两钟点起止）且单条计时 create
- **THEN** startTime SHALL 对应较早钟点、endTime 对应较晚钟点
- **AND** 系统 MUST NOT 仅因两个钟点而对单条 events 取消缓存命中并强制走分类

### Requirement: 有进行中时仍可插入闭合补记
当同设备同 eventId 已存在进行中记录（end_time=0）时，系统仍 SHALL 能通过 batch create 插入另一条 `endTime>0` 的闭合记录。系统 MUST NOT 为通过该场景而要求修改 Go 侧互斥逻辑（Go 仅拦截再次 endTime=0）。

#### Scenario: 进行中母乳时补记十分钟
- **WHEN** 设备上母乳已有进行中记录
- **AND** 用户确认「母乳10分钟」类闭合补记且 Python 提交 endTime>0
- **THEN** batch 对该 create SHALL 成功（或等价 ok）
- **AND** MUST NOT 因「已在进行中」失败

### Requirement: 无时长的单点开始仍开表
当计时 create 仅有开始钟点或「开始」语义、且无时长、无第二结束钟点时，系统 SHALL 继续以 `end_time=0` 开表。

#### Scenario: 开始母乳无时长
- **WHEN** 用户说「开始母乳」或「早上8点开始母乳」且无分钟时长、无结束钟点
- **THEN** 落库 endTime SHALL 为 0
