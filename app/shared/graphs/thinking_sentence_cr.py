"""
LLM 思考句界回车

业务说明：
客户端约定：thinking content 以 \\r 开头则清空前置、展示新短文案。
对 LLM reasoning 流式增量：上一句已在句界结束后，下一句开头前置 \\r；
禁止在句界字符后直接贴 \\r（否则最后一句会被清空）。
展示前去掉拉丁字母与常见 JSON / markdown 符号，避免字幕里出现字段名。
编排字幕 emit_thinking 不走本模块。
"""

from __future__ import annotations

from typing import List

# 句界：中文。！？与英文.!?（英文句界符号本身保留，字母另删）
_SENTENCE_END = frozenset("。！？.!?")

# 思考字幕不展示：拉丁字母 + 常见 JSON / markdown 格式符
_STRIP_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "{}[]\"'`:#*_"
)


def _strip_display_ascii(text: str) -> str:
    """
    去掉思考字幕里的拉丁字母与格式符号。

    保留中文、数字、空白、句界、段首用的 \\r。直接删掉，不换占位。
    """
    if not text:
        return ""
    return "".join(ch for ch in text if ch not in _STRIP_CHARS)


class ThinkingSentenceCrRewriter:
    """
    将 LLM thinking 增量改写为可分句清空的 SSE 片段列表。

    状态：上一发射片段是否以句界结束；若是，下一非空片段段首加 \\r。
    同一 feed 内若含「句界+下一句」，拆成多条，保证 \\r 落在事件 content 段首。
    """

    def __init__(self) -> None:
        # 上一句已在句界结束，等待下一句开头加 \\r
        self._awaiting_next = False

    def feed(self, delta: str) -> List[str]:
        """
        吃入一段 reasoning 增量，返回 0～N 条应透出的 content。

        先剔除拉丁字母与格式符号，再按句拆分。
        每条要么是句中追加（无段首 \\r），要么是新句（段首 \\r）。
        不返回单独的裸 \\r；剔空或仅空白不透出。
        """
        text = _strip_display_ascii(delta if delta is not None else "")
        if not text or not text.strip("\r"):
            # 全被剔空：不改句界等待状态，也不推空气泡
            return []
        # 仅空白（无 \\r）也不透出
        if not text.replace("\r", "").strip():
            return []

        out: List[str] = []
        buf: List[str] = []
        need_cr = self._awaiting_next

        def _emit() -> None:
            nonlocal need_cr
            if not buf:
                return
            piece = "".join(buf)
            buf.clear()
            # 仅空白不推；保留 need_cr 给下一句有字的片段
            if not piece.replace("\r", "").strip():
                return
            if need_cr:
                if not piece.startswith("\r"):
                    piece = "\r" + piece
                need_cr = False
            out.append(piece)

        for ch in text:
            buf.append(ch)
            if ch in _SENTENCE_END:
                _emit()
                # 句界已发出；下一句开头再加 \\r，句末本身不贴 \\r
                need_cr = True

        if buf:
            _emit()
            # 停在句中：尚未结束
            self._awaiting_next = False
        else:
            # 刚好停在句界
            self._awaiting_next = need_cr

        return out

    def flush(self) -> List[str]:
        """
        流结束时调用：不发送裸 \\r，避免清空最后一句字幕。
        本实现 feed 已即时吐出缓冲，故恒为空列表。
        """
        self._awaiting_next = False
        return []
