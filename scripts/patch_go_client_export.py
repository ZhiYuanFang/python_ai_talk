go_file = r"d:\work\go_ai_talk\internal\services\voice\python_ai_client.go"

with open(go_file, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "func pythonAIClientFromCfg() *PythonAIClient {",
    "func PythonAIClientFromCfg() *PythonAIClient {"
)

with open(go_file, "w", encoding="utf-8") as f:
    f.write(content)

print("python_ai_client.go exported successfully!")
