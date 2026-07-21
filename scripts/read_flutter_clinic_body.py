flutter_file = r"d:\work\flutter_ai_talk\app\lib\ui\widgets\clinic_answer_body.dart"

with open(flutter_file, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
for i, line in enumerate(lines[:150], 1):
    print(f"{i}: {line}")
