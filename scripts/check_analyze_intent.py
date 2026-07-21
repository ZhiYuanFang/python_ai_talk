go_file = r"d:\work\go_ai_talk\internal\services\voice\python_ai_client.go"

with open(go_file, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
in_struct = False
for i, line in enumerate(lines, 1):
    if "type AnalyzeIntentResponse struct" in line:
        in_struct = True
        print(f"{i}: {line}")
    elif in_struct and "}" in line and not "{" in line:
        print(f"{i}: {line}")
        break
    elif in_struct:
        print(f"{i}: {line}")
