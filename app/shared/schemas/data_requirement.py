"""
拉史数据需求模型

业务说明：
judge_data_requirement / fetch_history / care-alert 共用的筛选条件。
放在 shared，避免 clinic↔feeding 互引。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DataRequirement(BaseModel):
    """
    历史筛选需求。

    业务说明：
    event_ids 空表示不按事件过滤；time_range 可为枚举，拉史前常已换成 unix。
    """

    model_config = ConfigDict(extra="ignore")

    event_ids: List[str] = Field(default_factory=list)
    time_range: Optional[str] = "last_7_days"
    limit: int = 20
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    remark: Optional[str] = None
    remark_keyword: Optional[str] = None

    def as_window_dict(self) -> Dict[str, Any]:
        """供 resolve_window / filter 使用的浅字典。"""
        return self.model_dump(exclude_none=False)
