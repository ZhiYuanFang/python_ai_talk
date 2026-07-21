go_file = r"d:\work\go_ai_talk\internal\services\voice\python_ai_client.go"

with open(go_file, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
for i, line in enumerate(lines[:100], 1):
    print(f"{i}: {line}")
