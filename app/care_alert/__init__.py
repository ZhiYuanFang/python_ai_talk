"""
护理留意（care-alert）日分析模块

业务说明：
供 Go 编排内调：基于月龄、近期喂养历史与合格通识，由 LLM 产出「值得留意」列表。
不与 clinic 配额耦合；ignore/follow_up 固定意图在 Python 侧驱动通识质量飞轮。
"""
