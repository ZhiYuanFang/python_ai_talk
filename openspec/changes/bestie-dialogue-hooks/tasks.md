## 1. Clinic prompts

- [x] 1.1 Update `clinic_answer` system: 对话感引导（含点查/汇总先事实后引导）、同月龄代入边界、约 80 字；保留有据点名与安全规则
- [x] 1.2 Update `clinic_answer` user closing / length hints from 50→80 and encourage guiding close

## 2. Tip prompts

- [x] 2.1 Align `tip_answer` system + user closing with dialogue hooks, peer simulation, ~80 字

## 3. Tests

- [x] 3.1 Update/add unit tests for引导/同月龄/约 80 字 phrases; adjust any assertions still expecting 50 字
