"""
MySQL 连接与建表

业务说明：
与 Go 同址库；表前缀 agent_。启动时 ensure_schema。
无业务默认上游域名——仅存租户配置的完整 URL。
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Any, Generator, Optional

import pymysql
from pymysql.connections import Connection

from app.config.settings import settings

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agent_admin (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(128) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_tenant_pair (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  display_name VARCHAR(128) NOT NULL COMMENT '用户名/客户备注',
  g_token_hash CHAR(64) NOT NULL UNIQUE,
  a_token_hash CHAR(64) NOT NULL UNIQUE,
  g_token_plain VARCHAR(256) NOT NULL COMMENT '供控制台展示复制',
  a_token_plain VARCHAR(256) NOT NULL,
  g_enabled TINYINT(1) NOT NULL DEFAULT 1,
  a_enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_tool_endpoint (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  pair_id BIGINT NOT NULL,
  tool_key VARCHAR(64) NOT NULL,
  method VARCHAR(8) NOT NULL DEFAULT 'POST',
  url TEXT NOT NULL,
  upstream_auth VARCHAR(512) NULL COMMENT '可选上游 Bearer',
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_pair_tool (pair_id, tool_key),
  CONSTRAINT fk_endpoint_pair FOREIGN KEY (pair_id) REFERENCES agent_tenant_pair(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

_lock = threading.Lock()
_ready = False


def _connect() -> Connection:
    """新建一条 pymysql 连接。"""
    return pymysql.connect(
        host=settings.mysql_host,
        port=int(settings.mysql_port),
        user=settings.mysql_user,
        password=settings.mysql_password or "",
        database=settings.mysql_database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


@contextmanager
def db_conn() -> Generator[Connection, None, None]:
    """获取连接；用毕关闭。"""
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def ensure_schema() -> None:
    """
    建库（若不存在）并建表；幂等。

    Side Effects:
        可能 CREATE DATABASE；写 agent_* 表。
    """
    global _ready
    with _lock:
        if _ready:
            return
        # 先无库名连上，确保 database 存在
        bootstrap = pymysql.connect(
            host=settings.mysql_host,
            port=int(settings.mysql_port),
            user=settings.mysql_user,
            password=settings.mysql_password or "",
            charset="utf8mb4",
            autocommit=True,
        )
        try:
            with bootstrap.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{settings.mysql_database}` "
                    "DEFAULT CHARACTER SET utf8mb4"
                )
        finally:
            bootstrap.close()

        with db_conn() as conn:
            with conn.cursor() as cur:
                for stmt in _SCHEMA_SQL.split(";"):
                    s = stmt.strip()
                    if s:
                        cur.execute(s)
        _ready = True
        logger.info("agent_console schema ready db=%s", settings.mysql_database)


def try_ensure_schema() -> bool:
    """启动时尝试建表；失败返回 False 不阻断进程（便于无 DB 开发）。"""
    try:
        ensure_schema()
        return True
    except Exception as e:
        logger.warning("agent_console MySQL 不可用: %s", e)
        return False
