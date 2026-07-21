go_file = r"d:\work\go_ai_talk\api\v1\device_clinic_feedback_http.go"

content = """package v1

import (
	"github.com/gogf/gf/v2/frame/g"
)

// DeviceClinicFeedbackReq 诊疗反馈请求。
type DeviceClinicFeedbackReq struct {
	g.Meta        `path:"/device/api/clinic/feedback" method:"post" tags:"device" summary:"诊疗反馈"`
	AnswerId      string `json:"answerId" dc:"回答 ID（来自 answer_done 事件）"`
	Feedback      int    `json:"feedback" dc:"反馈值：1=thumbs up，-1=thumbs down"`
}

// DeviceClinicFeedbackRes 诊疗反馈响应。
type DeviceClinicFeedbackRes struct {
	Code    int    `json:"code" dc:"状态码：0=成功"`
	Message string `json:"message" dc:"提示信息"`
	Data    struct {
		AnswerId string `json:"answerId" dc:"回答 ID"`
		Feedback int    `json:"feedback" dc:"反馈值"`
	} `json:"data"`
}

// DeviceTipFeedbackReq 小贴士反馈请求。
type DeviceTipFeedbackReq struct {
	g.Meta        `path:"/device/api/tip/feedback" method:"post" tags:"device" summary:"小贴士反馈"`
	AnswerId      string `json:"answerId" dc:"回答 ID（来自 tip 响应）"`
	Feedback      int    `json:"feedback" dc:"反馈值：1=thumbs up，-1=thumbs down"`
}

// DeviceTipFeedbackRes 小贴士反馈响应。
type DeviceTipFeedbackRes struct {
	Code    int    `json:"code" dc:"状态码：0=成功"`
	Message string `json:"message" dc:"提示信息"`
	Data    struct {
		AnswerId string `json:"answerId" dc:"回答 ID"`
		Feedback int    `json:"feedback" dc:"反馈值"`
	} `json:"data"`
}
"""

with open(go_file, "w", encoding="utf-8") as f:
    f.write(content)

print("device_clinic_feedback_http.go created successfully!")
