"""
上游 HTTP（遗留文件名）

业务说明：
原直打 Go 的 HttpClient 已废弃；请使用 app.agent_console.upstream.call_upstream。
本模块仅再导出，避免旧 import 硬崩。
"""

from app.agent_console.upstream import call_upstream

__all__ = ["call_upstream"]


class HttpClient:
    """已废弃：无默认基址；请走 agent_console。"""

    async def close(self) -> None:
        return None


http_client = HttpClient()
