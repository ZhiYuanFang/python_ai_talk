"""
修复 Go 侧 filter.go 的未使用导入问题

业务说明：
filter.go 中导入了 crypto/sha256 和 encoding/hex，但这两个包未被使用，
因为缓存键生成函数在 cachekit 包中。需要移除这两个未使用的导入。
"""

import re

# 文件路径
file_path = r"d:\work\go_ai_talk\internal\services\history\filter.go"

# 读取文件
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 移除未使用的导入行
content = content.replace('\t"crypto/sha256"\n', '')
content = content.replace('\t"encoding/hex"\n', '')

# 写回文件
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("已修复 filter.go 的未使用导入问题")
