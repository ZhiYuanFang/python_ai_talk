"""
非事件规则名词

业务说明：
操作轨、播报、定位、备注的说法只在这里维护。正则和拼音缓存都从这些元组来。
两维共用的词只写一份。事件正式名和 extra_names 不写进本文件。
导入时建成拼音缓存，请求里不再转写词表。
"""

from __future__ import annotations

import re
from typing import Sequence, Tuple

from app.feeding.services.event_homophone import (
    Aligned,
    LexiconIndex,
    apply_lexicon_view,
    build_lexicon_index,
)

# 操作轨点查，也给播报用：问上一次记录。播报时优先已完成，并带上还在进行的那条
PRIOR_WORDS: Tuple[str, ...] = (
    "上次",  # 上一次发生的记录
    "上一次",  # 同上，说法更完整
    "最近一次",  # 最近的那一次，仍按点查而不是日汇总
)

# 操作轨·预测用量：这次还要吃/喝多少，不是查历史
PREDICT_AMOUNT_WORDS: Tuple[str, ...] = (
    "这次要吃多少",  # 下一顿吃多少
    "这次要喝多少",  # 下一顿喝多少
    "要吃多少",  # 不带「这次」的吃量预测
    "要喝多少",  # 不带「这次」的喝量预测
    "大概要吃多少",  # 大约还要吃多少
    "大概要喝多少",  # 大约还要喝多少
    "大概还要吃多少",  # 强调还没吃完、还要补多少
)
# 操作轨·查记录用量：已经发生的量，按点查记录
RECORD_AMOUNT_WORDS: Tuple[str, ...] = (
    "吃了多少",  # 查已经吃了的量
    "喝了多少",  # 查已经喝了的量
    "拉了多少",  # 查大便量
    "尿了多少",  # 查小便量
)
# 操作轨·预测时长：这次准备吃/喝/睡多久
PREDICT_DURATION_WORDS: Tuple[str, ...] = (
    "这次要吃多久",  # 预测这一顿吃多久
    "这次要喝多久",  # 预测这一顿喝多久
    "这次要睡多久",  # 预测这一觉睡多久
    "要吃多久",  # 不带「这次」的吃时预测
    "要喝多久",  # 不带「这次」的喝时预测
)
# 操作轨·查记录时长：已经睡/吃/喝/拉了多久，按点查记录
RECORD_DURATION_WORDS: Tuple[str, ...] = (
    "睡了多久",  # 查已经睡了多久
    "吃了多久",  # 查已经吃了多久
    "喝了多久",  # 查已经喝了多久
    "拉了多久",  # 查这次大便持续多久
)
# 操作轨·预测时间点：还要多久、几点再吃，回答剩余时间
PREDICT_WHEN_WORDS: Tuple[str, ...] = (
    "还要多久",  # 还要过多久
    "还要多长时间",  # 同上，说法更长
    "还有多久",  # 距离下一件还剩多久
    "几点吃",  # 问下一次吃的钟点
    "什么时候吃",  # 问下一次吃的时间
    "什么时候喝",  # 问下一次喝的时间
)
# 操作轨·查记录次数：走日汇总，不走单次点查
RECORD_POINT_EXTRA_WORDS: Tuple[str, ...] = (
    "几次",  # 问一天里发生了几次
    "多少次",  # 同上
)
# 操作轨·记一笔：句里没有疑问词时记成新记录。结束计时的「睡醒了」不在这里
CREATE_VERBS: Tuple[str, ...] = (
    "吃了",  # 记一笔进食
    "喝了",  # 记一笔喝奶/喝水
    "拉了",  # 记一笔大便
    "尿了",  # 记一笔小便
    "睡着了",  # 记一笔开始睡觉
    "睡了",  # 记一笔睡觉；「睡了多久」会被查记录先接住
    "开始",  # 记一笔开始计时
)
# 操作轨·疑问词：句里有这些词时，不把「吃了/睡了」收成记一笔
QUESTION_WORDS: Tuple[str, ...] = (
    "多少",  # 在问数量
    "多久",  # 在问时长
    "几次",  # 在问次数
    "什么时候",  # 在问时间
    "还要",  # 在问还剩多少或还要多久
)

# 定位·进行中：改删时找还没结束的那条
LOCATE_OPEN_WORDS: Tuple[str, ...] = (
    "正在进行",  # 找当前没结束的记录
    "还没结束",  # 同上
    "进行中的",  # 同上
)
# 定位·已完成：改删时优先已经做完的那次
LOCATE_DONE_WORDS: Tuple[str, ...] = (
    "已完成的",  # 找做完的记录
    "做完的那次",  # 同上
)
# 定位·最近一条：改删时找时间上最近的一条
LOCATE_LATEST_WORDS: Tuple[str, ...] = (
    "最近一条",  # 找最近写入的一条
    "上一条",  # 找上一条
    "刚才那条",  # 找刚刚说的那条
)

# 播报·进行了多久：点查时如果记录还在进行，报已经过了多久
ELAPSED_WORDS: Tuple[str, ...] = (
    "多久了",  # 问当前这次已经持续多久
    "多长时间了",  # 同上
)

# 备注·时段：这些词只说明何时，不是备注明细，剥掉后不再送备注模型
PERIOD_WORDS: Tuple[str, ...] = (
    "凌晨",  # 一天中的时段，不算备注
    "早上",  # 一天中的时段，不算备注
    "早晨",  # 一天中的时段，不算备注
    "上午",  # 一天中的时段，不算备注
    "中午",  # 一天中的时段，不算备注
    "下午",  # 一天中的时段，不算备注
    "傍晚",  # 一天中的时段，不算备注
    "晚上",  # 一天中的时段，不算备注
    "夜里",  # 一天中的时段，不算备注
    "晚间",  # 一天中的时段，不算备注
    "昨天",  # 哪一天，不算备注
    "今天",  # 哪一天，不算备注
    "昨日",  # 哪一天，不算备注
    "今日",  # 哪一天，不算备注
    "昨晚",  # 昨天晚上，不算备注
)
# 备注·记一笔套话：剥掉后看是否还剩「有点凉」这类明细。比记一笔多「喂了」
REMARK_VERBS: Tuple[str, ...] = (
    "吃了",  # 进食套话，本身不是备注
    "喝了",  # 喝奶套话
    "拉了",  # 大便套话
    "尿了",  # 小便套话
    "睡着了",  # 入睡套话
    "睡了",  # 睡觉套话
    "喂了",  # 喂养套话，只在备注剥离时使用
)


def words_pattern(words: Sequence[str]) -> re.Pattern[str]:
    """用名词元组拼正则。长词在前，避免短词截断。"""
    ordered = sorted({w for w in words if w}, key=len, reverse=True)
    if not ordered:
        return re.compile(r"(?!)")
    return re.compile("|".join(re.escape(word) for word in ordered))


def _uniq(*groups: Sequence[str]) -> Tuple[str, ...]:
    """按出现顺序去重，供一份视图词表使用。"""
    out: List[str] = []
    seen: set[str] = set()
    for group in groups:
        for word in group:
            if word and word not in seen:
                seen.add(word)
                out.append(word)
    return tuple(out)


# 操作轨视图词表：预测、查记录、记一笔、疑问词放在同一次最长匹配里
OP_VIEW_WORDS = _uniq(
    PREDICT_AMOUNT_WORDS,
    RECORD_AMOUNT_WORDS,
    PREDICT_DURATION_WORDS,
    RECORD_DURATION_WORDS,
    PREDICT_WHEN_WORDS,
    PRIOR_WORDS,
    RECORD_POINT_EXTRA_WORDS,
    CREATE_VERBS,
    QUESTION_WORDS,
)
# 播报视图词表：只换「上次」和「多久了」，不带动操作轨的其它说法
SPEAK_VIEW_WORDS = _uniq(PRIOR_WORDS, ELAPSED_WORDS)
# 定位视图词表：只换改删定位的三种说法
LOCATE_VIEW_WORDS = _uniq(LOCATE_OPEN_WORDS, LOCATE_DONE_WORDS, LOCATE_LATEST_WORDS)
# 备注视图词表：只换时段和记一笔套话，不改事件名
REMARK_VIEW_WORDS = _uniq(PERIOD_WORDS, REMARK_VERBS)

# 导入时建成，后续加名词会在进程重启后进入缓存
_OP_INDEX: LexiconIndex = build_lexicon_index(OP_VIEW_WORDS)
_SPEAK_INDEX: LexiconIndex = build_lexicon_index(SPEAK_VIEW_WORDS)
_LOCATE_INDEX: LexiconIndex = build_lexicon_index(LOCATE_VIEW_WORDS)
_REMARK_INDEX: LexiconIndex = build_lexicon_index(REMARK_VIEW_WORDS)


def apply_op_view(text: str, syllables: Aligned | None) -> str:
    """操作轨视图。只替换操作轨名词。"""
    return apply_lexicon_view(text, syllables, _OP_INDEX, label="操作轨")


def apply_speak_view(text: str, syllables: Aligned | None) -> str:
    """点查播报视图。"""
    return apply_lexicon_view(text, syllables, _SPEAK_INDEX, label="播报")


def apply_locate_view(text: str, syllables: Aligned | None) -> str:
    """改删定位视图。"""
    return apply_lexicon_view(text, syllables, _LOCATE_INDEX, label="定位")


def apply_remark_view(text: str, syllables: Aligned | None) -> str:
    """备注视图。只替换时段词和记一笔套话。"""
    return apply_lexicon_view(text, syllables, _REMARK_INDEX, label="备注")
