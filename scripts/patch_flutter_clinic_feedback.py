import os

flutter_dir = r"d:\work\flutter_ai_talk"

print("=== Searching for clinic-related files in Flutter project ===")

for root, dirs, files in os.walk(flutter_dir):
    for file in files:
        if file.endswith(".dart"):
            filepath = os.path.join(root, file)
            if "clinic" in file.lower() or "feedback" in file.lower():
                print(f"Found: {filepath}")

print("\n=== Searching for answer_done handling ===")
for root, dirs, files in os.walk(flutter_dir):
    for file in files:
        if file.endswith(".dart"):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "answer_done" in content or "answerId" in content:
                        print(f"Found in: {filepath}")
            except:
                pass
