go_file = r"d:\work\go_ai_talk\internal\services\voice\voice_chat_understanding.go"

with open(go_file, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
for i, line in enumerate(lines[:100], 1):
    if "IntentEvent" in line or "pythonAIClientFromCfg" in line or "pythonResp" in line:
        print(f"{i}: {line}")
