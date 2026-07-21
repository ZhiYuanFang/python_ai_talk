flutter_file = r"d:\work\flutter_ai_talk\app\lib\ui\pangbao_ai_screen.dart"

with open(flutter_file, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
for i, line in enumerate(lines[500:650], 501):
    print(f"{i}: {line}")
