import os

go_dir = r"d:\work\go_ai_talk\internal\services\voice"

for filename in os.listdir(go_dir):
    if filename.endswith(".go"):
        filepath = os.path.join(go_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "pythonAIClientFromCfg" in content:
            content = content.replace("pythonAIClientFromCfg", "PythonAIClientFromCfg")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Updated {filename}")

print("All internal references fixed!")
