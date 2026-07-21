go_file = r"d:\work\go_ai_talk\internal\controller\device_clinic_feedback_controller.go"

content = """package controller

import (
	"context"

	"hello/api/v1"
	"hello/internal/services/voice"

	"github.com/gogf/gf/v2/frame/g"
)

// DeviceClinicFeedbackController 诊疗反馈控制器。
type DeviceClinicFeedbackController struct{}

// ClinicFeedback 诊疗反馈。
func (c *DeviceClinicFeedbackController) ClinicFeedback(ctx context.Context, req *v1.DeviceClinicFeedbackReq) (res *v1.DeviceClinicFeedbackRes, err error) {
	if req.Feedback != 1 && req.Feedback != -1 {
		return &v1.DeviceClinicFeedbackRes{
			Code:    400,
			Message: "反馈值必须为 1（thumbs up）或 -1（thumbs down）",
		}, nil
	}
	pythonClient := voice.PythonAIClientFromCfg()
	pythonResp, pythonErr := pythonClient.ClinicFeedback(ctx, &voice.FeedbackRequest{
		AnswerID: req.AnswerId,
		Feedback: req.Feedback,
	})
	if pythonErr != nil {
		g.Log().Warning(ctx, "[Clinic Feedback] 调用 Python 反馈服务失败: ", pythonErr)
		return &v1.DeviceClinicFeedbackRes{
			Code:    500,
			Message: "反馈提交失败",
		}, nil
	}
	return &v1.DeviceClinicFeedbackRes{
		Code:    pythonResp.Code,
		Message: pythonResp.Message,
		Data: struct {
			AnswerId string `json:"answerId"`
			Feedback int    `json:"feedback"`
		}{
			AnswerId: pythonResp.Data.AnswerID,
			Feedback: pythonResp.Data.Feedback,
		},
	}, nil
}

// TipFeedback 小贴士反馈。
func (c *DeviceClinicFeedbackController) TipFeedback(ctx context.Context, req *v1.DeviceTipFeedbackReq) (res *v1.DeviceTipFeedbackRes, err error) {
	if req.Feedback != 1 && req.Feedback != -1 {
		return &v1.DeviceTipFeedbackRes{
			Code:    400,
			Message: "反馈值必须为 1（thumbs up）或 -1（thumbs down）",
		}, nil
	}
	pythonClient := voice.PythonAIClientFromCfg()
	pythonResp, pythonErr := pythonClient.TipFeedback(ctx, &voice.FeedbackRequest{
		AnswerID: req.AnswerId,
		Feedback: req.Feedback,
	})
	if pythonErr != nil {
		g.Log().Warning(ctx, "[Tip Feedback] 调用 Python 反馈服务失败: ", pythonErr)
		return &v1.DeviceTipFeedbackRes{
			Code:    500,
			Message: "反馈提交失败",
		}, nil
	}
	return &v1.DeviceTipFeedbackRes{
		Code:    pythonResp.Code,
		Message: pythonResp.Message,
		Data: struct {
			AnswerId string `json:"answerId"`
			Feedback int    `json:"feedback"`
		}{
			AnswerId: pythonResp.Data.AnswerID,
			Feedback: pythonResp.Data.Feedback,
		},
	}, nil
}
"""

with open(go_file, "w", encoding="utf-8") as f:
    f.write(content)

print("device_clinic_feedback_controller.go created successfully!")
