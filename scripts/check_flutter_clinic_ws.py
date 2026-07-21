flutter_file = r"d:\work\flutter_ai_talk\app\lib\voice\clinic_ws_client.dart"

with open(flutter_file, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
for i, line in enumerate(lines, 1):
    if "answer_done" in line or "answerId" in line or "answer_id" in line:
        print(f"{i}: {line}")
