## 1. Clinic prompts

- [x] 1.1 Rewrite `build_clinic_answer_system_prompt`: experienced bestie; grounded cite rules; remove “记录只作背景”; keep safety + point-query/summary; ~50字 for advice
- [x] 1.2 Update `build_clinic_answer_user_message` closing instructions: conditional on history / chat_context / neither; keep record-first for lookup/summary

## 2. Tip prompts

- [x] 2.1 Align `tip_answer` system + user closing with same grounded-bestie rules (event opener, ~50字, cite near history/chat when present)

## 3. Verify

- [x] 3.1 Add lightweight unit tests asserting key constraint phrases appear in built prompts for (history only / chat only / neither) cases
- [x] 3.2 Smoke-read: stream_response / generate_clinic_answer / tip stream still call the updated builders; note Q&A fast-path as out of scope
