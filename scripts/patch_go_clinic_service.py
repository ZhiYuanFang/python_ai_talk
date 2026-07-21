go_file = r"d:\work\go_ai_talk\internal\services\voice\clinic_service.go"

with open(go_file, "r", encoding="utf-8") as f:
    content = f.read()

old_call = """\tthinking, answer, streamErr := s.streamClinicLLMHeld(turnCtx, profile, baby, summary, question, prior, clinicStreamCallbacks{
\t\tOnThinkingDelta: func(delta string) error {
\t\t\tif err := turnCtx.Err(); err != nil {
\t\t\t\treturn err
\t\t\t}
\t\t\treturn writeJSON(map[string]interface{}{"type": "thinking_delta", "delta": delta, "turnId": turnID})
\t\t},
\t\tOnAnswerDelta: func(delta string) error {
\t\t\tif err := turnCtx.Err(); err != nil {
\t\t\t\treturn err
\t\t\t}
\t\t\treturn writeJSON(map[string]interface{}{"type": "answer_delta", "delta": delta, "turnId": turnID})
\t\t},
\t})"""

new_call = """\tthinking, answer, answerID, streamErr := s.streamClinicLLMHeld(turnCtx, profile, baby, summary, question, prior, clinicStreamCallbacks{
\t\tOnThinkingDelta: func(delta string) error {
\t\t\tif err := turnCtx.Err(); err != nil {
\t\t\t\treturn err
\t\t\t}
\t\t\treturn writeJSON(map[string]interface{}{"type": "thinking_delta", "delta": delta, "turnId": turnID})
\t\t},
\t\tOnAnswerDelta: func(delta string) error {
\t\t\tif err := turnCtx.Err(); err != nil {
\t\t\t\treturn err
\t\t\t}
\t\t\treturn writeJSON(map[string]interface{}{"type": "answer_delta", "delta": delta, "turnId": turnID})
\t\t},
\t})"""

content = content.replace(old_call, new_call)

old_answer_done = """\treturn writeJSON(map[string]interface{}{
\t\t"type":     "answer_done",
\t\t"turnId":   turnID,
\t\t"thinking": thinking,
\t\t"answer":   answer,
\t})"""

new_answer_done = """\treturn writeJSON(map[string]interface{}{
\t\t"type":      "answer_done",
\t\t"turnId":    turnID,
\t\t"thinking":  thinking,
\t\t"answer":    answer,
\t\t"answerId":  answerID,
\t})"""

content = content.replace(old_answer_done, new_answer_done)

with open(go_file, "w", encoding="utf-8") as f:
    f.write(content)

print("clinic_service.go updated successfully!")
