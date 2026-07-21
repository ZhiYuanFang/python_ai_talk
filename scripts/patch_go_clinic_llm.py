go_file = r"d:\work\go_ai_talk\internal\services\voice\clinic_llm.go"

with open(go_file, "r", encoding="utf-8") as f:
    content = f.read()

old_struct = """type clinicStreamCallbacks struct {
	OnThinkingDelta func(delta string) error
	OnAnswerDelta   func(delta string) error
}"""

new_struct = """type clinicStreamCallbacks struct {
	OnThinkingDelta func(delta string) error
	OnAnswerDelta   func(delta string) error
	OnDone          func(answerID string) error
}"""

content = content.replace(old_struct, new_struct)

old_func = """// streamClinicLLMHeld 在调用方已持 clinic 闸门槽位时发起流式请求。
// 仅调用 Python 微服务，Python 不可用时直接返回错误，由上层返回降级提示语。
func (s *ClinicService) streamClinicLLMHeld(ctx context.Context, profile aimodel.Profile, baby clinicBabyProfile, summaryJSON, question string, prior []map[string]string, cb clinicStreamCallbacks) (thinking, answer string, err error) {
	deviceNo := baby.deviceNo
	if deviceNo != "" {
		pythonClient := pythonAIClientFromCfg()
		pythonThinking, pythonAnswer, pythonErr := pythonClient.ClinicStream(ctx, &ClinicStreamRequest{
			Question: question,
			DeviceNo: deviceNo,
			Model: PythonModelCfg{
				Provider:    string(profile.Provider),
				Name:        profile.Model,
				MaxInFlight: 1,
			},
		}, &ClinicStreamCallback{
			OnThinking: cb.OnThinkingDelta,
			OnAnswer:   cb.OnAnswerDelta,
		})
		if pythonErr == nil {
			return pythonThinking, pythonAnswer, nil
		}
		glog.Warningf(ctx, "[Python AI] 诊疗流式调用失败。deviceNo=%s err=%v", deviceNo, pythonErr)
		return "", "", pythonErr
	}
	return "", "", errors.New("诊疗服务设备号缺失")
}"""

new_func = """// streamClinicLLMHeld 在调用方已持 clinic 闸门槽位时发起流式请求。
// 仅调用 Python 微服务，Python 不可用时直接返回错误，由上层返回降级提示语。
func (s *ClinicService) streamClinicLLMHeld(ctx context.Context, profile aimodel.Profile, baby clinicBabyProfile, summaryJSON, question string, prior []map[string]string, cb clinicStreamCallbacks) (thinking, answer, answerID string, err error) {
	deviceNo := baby.deviceNo
	if deviceNo != "" {
		pythonClient := pythonAIClientFromCfg()
		pythonResp, pythonErr := pythonClient.ClinicStream(ctx, &ClinicStreamRequest{
			Question: question,
			DeviceNo: deviceNo,
			Model: PythonModelCfg{
				Provider:    string(profile.Provider),
				Name:        profile.Model,
				MaxInFlight: 1,
			},
		}, &ClinicStreamCallback{
			OnThinking: cb.OnThinkingDelta,
			OnAnswer:   cb.OnAnswerDelta,
			OnDone:     cb.OnDone,
		})
		if pythonErr == nil {
			return pythonResp.Thinking, pythonResp.Answer, pythonResp.AnswerID, nil
		}
		glog.Warningf(ctx, "[Python AI] 诊疗流式调用失败。deviceNo=%s err=%v", deviceNo, pythonErr)
		return "", "", "", pythonErr
	}
	return "", "", "", errors.New("诊疗服务设备号缺失")
}"""

content = content.replace(old_func, new_func)

old_func2 = """// streamClinicLLM 经 LaneClinic 调用上游流式接口（内部 Acquire）。
func (s *ClinicService) streamClinicLLM(ctx context.Context, baby clinicBabyProfile, summaryJSON, question string, prior []map[string]string, cb clinicStreamCallbacks) (thinking, answer string, err error) {
	profile, err := aimodel.LoadProfile(ctx, aimodel.LaneClinic)
	if err != nil {
		return "", "", err
	}
	return s.streamClinicLLMHeld(ctx, profile, baby, summaryJSON, question, prior, cb)
}"""

new_func2 = """// streamClinicLLM 经 LaneClinic 调用上游流式接口（内部 Acquire）。
func (s *ClinicService) streamClinicLLM(ctx context.Context, baby clinicBabyProfile, summaryJSON, question string, prior []map[string]string, cb clinicStreamCallbacks) (thinking, answer, answerID string, err error) {
	profile, err := aimodel.LoadProfile(ctx, aimodel.LaneClinic)
	if err != nil {
		return "", "", "", err
	}
	return s.streamClinicLLMHeld(ctx, profile, baby, summaryJSON, question, prior, cb)
}"""

content = content.replace(old_func2, new_func2)

with open(go_file, "w", encoding="utf-8") as f:
    f.write(content)

print("clinic_llm.go updated successfully!")
