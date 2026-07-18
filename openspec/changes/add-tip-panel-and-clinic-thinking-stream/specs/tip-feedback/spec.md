## ADDED Requirements

### Requirement: 小贴士反馈按钮展示
Flutter 小贴士组件右下角 SHALL 展示两个反馈按钮：手指向上图标（表示认同小贴士）和手指向下图标（表示不认同小贴士）。

#### Scenario: 反馈按钮初始展示
- **WHEN** 小贴士内容展示完成（done 状态）
- **THEN** Flutter SHALL 在小贴士组件右下角展示 👍 和 👎 两个反馈按钮，均为可点击状态

### Requirement: 反馈按钮点击交互
用户点击反馈按钮后，该按钮 SHALL 变灰（不可点击），仅保留用户选择的反馈按钮（隐藏未选中的按钮），并展示 toast 提示。

#### Scenario: 点击认同按钮
- **WHEN** 用户点击 👍 按钮
- **THEN** Flutter SHALL 将 👍 按钮变灰不可点击，隐藏 👎 按钮，展示 toast 提示"感谢反馈"，并发起反馈请求到 Go `/tip/feedback` 接口

#### Scenario: 点击不认同按钮
- **WHEN** 用户点击 👎 按钮
- **THEN** Flutter SHALL 将 👎 按钮变灰不可点击，隐藏 👍 按钮，展示 toast 提示"感谢反馈"，并发起反馈请求到 Go `/tip/feedback` 接口

#### Scenario: 反馈后不可更改
- **WHEN** 用户已点击某个反馈按钮并完成反馈
- **THEN** Flutter SHALL NOT 允许再次点击或更改反馈

### Requirement: 反馈数据存储
Go history service SHALL 接收 Flutter 的反馈请求，将反馈结果记录到 `ai_voice_history.tip` 表，存储字段包含：事件id、事件名、宝宝月龄、wx.id、反馈内容、反馈结果。

#### Scenario: 存储认同反馈
- **WHEN** Flutter 发送反馈请求，feedback_result=1（认同）
- **THEN** Go history service SHALL 更新 ai_voice_history.tip 表对应记录的 feedback_result=1、feedback_at=当前时间戳

#### Scenario: 存储不认同反馈
- **WHEN** Flutter 发送反馈请求，feedback_result=-1（不认同）
- **THEN** Go history service SHALL 更新 ai_voice_history.tip 表对应记录的 feedback_result=-1、feedback_at=当前时间戳

#### Scenario: 反馈请求包含完整上下文
- **WHEN** Flutter 发送反馈请求
- **THEN** 请求 SHALL 包含 tip_id（小贴士记录ID）和 feedback_result（1 或 -1），Go history service SHALL 据此更新对应记录
