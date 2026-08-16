"""
租户 G/A 与 tool URL 仓储

业务说明：
成对签发、G 生效失效、按 token 哈希查找、按 A 解析 tool 完整 URL。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.agent_console.catalog import TOOL_CATALOG
from app.agent_console.db import db_conn, ensure_schema
from app.agent_console.tokens import hash_token, new_token
from app.config.settings import settings

logger = logging.getLogger(__name__)


def seed_admin_if_needed() -> None:
    """若无管理员则写入种子账密（密码存 sha256）。"""
    ensure_schema()
    from app.agent_console.tokens import hash_token as _h

    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM agent_admin WHERE username=%s", (settings.agent_admin_username,))
            if cur.fetchone():
                return
            cur.execute(
                "INSERT INTO agent_admin (username, password_hash) VALUES (%s, %s)",
                (settings.agent_admin_username, _h(settings.agent_admin_password)),
            )
            logger.info("已写入管理员种子用户 %s", settings.agent_admin_username)


def verify_admin(username: str, password: str) -> bool:
    """校验管理员账密。"""
    ensure_schema()
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT password_hash FROM agent_admin WHERE username=%s",
                (username.strip(),),
            )
            row = cur.fetchone()
    if not row:
        return False
    return row["password_hash"] == hash_token(password)


def create_pair(display_name: str) -> Dict[str, Any]:
    """
    成对签发 G+A（1:1）。

    Returns:
        含明文 g_token / a_token 与 pair id
    """
    ensure_schema()
    name = (display_name or "").strip() or "unnamed"
    g_plain = new_token("gw")
    a_plain = new_token("api")
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_tenant_pair
                (display_name, g_token_hash, a_token_hash, g_token_plain, a_token_plain, g_enabled, a_enabled)
                VALUES (%s,%s,%s,%s,%s,1,1)
                """,
                (name, hash_token(g_plain), hash_token(a_plain), g_plain, a_plain),
            )
            pair_id = cur.lastrowid
    return {
        "id": pair_id,
        "display_name": name,
        "g_token": g_plain,
        "a_token": a_plain,
        "g_enabled": True,
        "a_enabled": True,
    }


def list_pairs() -> List[Dict[str, Any]]:
    """管理员列表（含明文便于复制；仅管理员接口调用）。"""
    ensure_schema()
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, display_name, g_token_plain, a_token_plain, g_enabled, a_enabled, created_at
                FROM agent_tenant_pair ORDER BY id DESC
                """
            )
            rows = cur.fetchall() or []
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "display_name": r["display_name"],
                "g_token": r["g_token_plain"],
                "a_token": r["a_token_plain"],
                "g_enabled": bool(r["g_enabled"]),
                "a_enabled": bool(r["a_enabled"]),
                "created_at": str(r.get("created_at") or ""),
            }
        )
    return out


def set_g_enabled(pair_id: int, enabled: bool) -> bool:
    """设置 G 生效/失效。"""
    ensure_schema()
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE agent_tenant_pair SET g_enabled=%s WHERE id=%s",
                (1 if enabled else 0, pair_id),
            )
            return cur.rowcount > 0


def find_pair_by_token(raw: str) -> Optional[Dict[str, Any]]:
    """
    用 G 或 A 明文查找租户对。

    Returns:
        pair 字典（含 plain tokens）或 None
    """
    ensure_schema()
    h = hash_token(raw)
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM agent_tenant_pair
                WHERE g_token_hash=%s OR a_token_hash=%s
                LIMIT 1
                """,
                (h, h),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "g_token": row["g_token_plain"],
        "a_token": row["a_token_plain"],
        "g_enabled": bool(row["g_enabled"]),
        "a_enabled": bool(row["a_enabled"]),
        "matched": "g" if row["g_token_hash"] == h else "a",
    }


def find_pair_by_g_hash(g_raw: str) -> Optional[Dict[str, Any]]:
    """门禁：仅按 G 查找且须 enabled。"""
    ensure_schema()
    h = hash_token(g_raw)
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM agent_tenant_pair WHERE g_token_hash=%s LIMIT 1",
                (h,),
            )
            row = cur.fetchone()
    if not row:
        return None
    if not row["g_enabled"]:
        return {"id": row["id"], "g_enabled": False}
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "g_enabled": True,
        "a_token": row["a_token_plain"],
        "a_enabled": bool(row["a_enabled"]),
    }


def find_pair_by_a(a_raw: str) -> Optional[Dict[str, Any]]:
    """Tools：按 A 查找；A 须 enabled。"""
    ensure_schema()
    h = hash_token(a_raw)
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM agent_tenant_pair WHERE a_token_hash=%s LIMIT 1",
                (h,),
            )
            row = cur.fetchone()
    if not row or not row["a_enabled"]:
        return None
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "g_token": row["g_token_plain"],
        "a_token": row["a_token_plain"],
        "g_enabled": bool(row["g_enabled"]),
        "a_enabled": True,
    }


def get_endpoint(pair_id: int, tool_key: str) -> Optional[Dict[str, Any]]:
    """取某槽位完整 URL。"""
    ensure_schema()
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tool_key, method, url, upstream_auth
                FROM agent_tool_endpoint WHERE pair_id=%s AND tool_key=%s
                """,
                (pair_id, tool_key),
            )
            return cur.fetchone()


def list_endpoints(pair_id: int) -> List[Dict[str, Any]]:
    """列出租户已配槽位。"""
    ensure_schema()
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tool_key, method, url, upstream_auth FROM agent_tool_endpoint WHERE pair_id=%s",
                (pair_id,),
            )
            return list(cur.fetchall() or [])


def upsert_endpoint(
    pair_id: int,
    tool_key: str,
    url: str,
    *,
    method: str = "POST",
    upstream_auth: str = "",
) -> None:
    """保存槽位完整 URL。"""
    ensure_schema()
    keys = {x["key"] for x in TOOL_CATALOG}
    if tool_key not in keys:
        raise ValueError(f"未知 tool_key: {tool_key}")
    url = (url or "").strip()
    if not url:
        raise ValueError("url 不能为空")
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_tool_endpoint (pair_id, tool_key, method, url, upstream_auth)
                VALUES (%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE method=VALUES(method), url=VALUES(url),
                  upstream_auth=VALUES(upstream_auth)
                """,
                (pair_id, tool_key, method.upper(), url, upstream_auth or None),
            )
