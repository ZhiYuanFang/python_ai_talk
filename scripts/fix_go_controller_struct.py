go_file = r"d:\work\go_ai_talk\internal\controller\device_clinic_feedback_controller.go"

with open(go_file, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    `Data: struct {
			AnswerId string ` + "`json:\"answerId\"`" + `
			Feedback int    ` + "`json:\"feedback\"`" + `
		}{
			AnswerId: pythonResp.Data.AnswerID,
			Feedback: pythonResp.Data.Feedback,
		},`,
    `Data: v1.DeviceClinicFeedbackRes_Data{
			AnswerId: pythonResp.Data.AnswerID,
			Feedback: pythonResp.Data.Feedback,
		},`
)

content = content.replace(
    `Data: struct {
			AnswerId string ` + "`json:\"answerId\"`" + `
			Feedback int    ` + "`json:\"feedback\"`" + `
		}{
			AnswerId: pythonResp.Data.AnswerID,
			Feedback: pythonResp.Data.Feedback,
		},`,
    `Data: v1.DeviceTipFeedbackRes_Data{
			AnswerId: pythonResp.Data.AnswerID,
			Feedback: pythonResp.Data.Feedback,
		},`
)

with open(go_file, "w", encoding="utf-8") as f:
    f.write(content)

print("Controller struct fixed successfully!")
