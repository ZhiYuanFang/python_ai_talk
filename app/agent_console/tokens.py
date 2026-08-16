"""
Token 哈希与生成

业务说明：
G/A 生成时返回明文；库内同时存 sha256 索引与明文（供 API 管理页再次展示复制）。
生产可改为加密列；本期按产品要求支持页内复制。
"""

from __future__ import annotations

import hashlib
import secrets


def hash_token(raw: str) -> str:
    """对 token 明文做 sha256 hex。"""
    return hashlib.sha256((raw or "").strip().encode("utf-8")).hexdigest()


def new_token(prefix: str) -> str:
    """
    生成带前缀的随机 token。

    Args:
        prefix: 如 gw / api，便于肉眼区分 G/A
    """
    return f"{prefix}_{secrets.token_urlsafe(32)}"
