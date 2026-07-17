# -*- coding: utf-8 -*-
"""在 http_targets.go 中新增 HistoryFilterPath 方法"""

import os

file_path = r"d:\work\go_ai_talk\internal\services\contracts\http_targets.go"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

if "HistoryFilterPath" in content:
    print("[跳过] HistoryFilterPath 已存在")
else:
    target = 'func (t HTTPTargets) HistoryEventEndLatestPath() string {\n\treturn "/device/history/api/event/end-latest"\n}'
    new_method = '''
func (t HTTPTargets) HistoryFilterPath() string {
	return "/device/history/api/filter"
}'''
    content = content.replace(target, target + new_method)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[完成] 新增 HistoryFilterPath 方法")
