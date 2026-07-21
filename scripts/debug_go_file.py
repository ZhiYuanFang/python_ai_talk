go_file = r"d:\work\go_ai_talk\internal\services\voice\python_ai_client.go"

with open(go_file, "r", encoding="utf-8") as f:
    content = f.read()

print("=== Searching for IntentEvent ===")
if "type IntentEvent struct" in content:
    print("FOUND: IntentEvent struct")
else:
    print("NOT FOUND: IntentEvent struct")

print("\n=== Searching for EventId field ===")
if 'EventId    string' in content:
    print("FOUND: EventId field")
else:
    print("NOT FOUND: EventId field")

print("\n=== Lines 50-80 ===")
lines = content.split("\n")
for i, line in enumerate(lines[49:80], 50):
    print(f"{i}: {repr(line)}")
