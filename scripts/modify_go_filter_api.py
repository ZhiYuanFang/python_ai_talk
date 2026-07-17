# -*- coding: utf-8 -*-
"""
修改 Go 侧历史记录筛选 API 相关文件

业务说明：
1. 在 device_history_http.go 中新增 Filter 请求/响应模型
2. 在 runtime_contracts.go 中新增 ListHistoryFilter 方法声明
3. 在 history 服务中新增 filter.go 实现
4. 在 device_history.go controller 中新增 Filter 方法
"""

import os

GO_PROJECT_DIR = r"d:\work\go_ai_talk"


def add_filter_model():
    """新增 Filter 请求/响应模型"""
    file_path = os.path.join(GO_PROJECT_DIR, r"api\v1\device_history_http.go")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_code = '''
// DeviceHistoryFilterReq 多条件筛选历史记录（多事件ID + 时间范围）。
// 事件ID使用稳定标识 eventIds（事件名会变但ID不变），eventIds 为逗号分隔的ID列表。
type DeviceHistoryFilterReq struct {
	g.Meta    `path:"/device/history/api/filter" method:"get" tags:"device" summary:"历史记录筛选（多事件ID+时间范围）"`
	DeviceNo  string `json:"deviceNo"  p:"deviceNo"  dc:"设备号"`
	EventIds  string `json:"eventIds"  p:"eventIds"  dc:"事件ID列表，逗号分隔，如 1,2,3；为空表示全部事件"`
	StartTime int64  `json:"startTime" p:"startTime" dc:"开始时间，Unix 秒；0 表示不限制开始"`
	EndTime   int64  `json:"endTime"   p:"endTime"   dc:"结束时间，Unix 秒；0 表示不限制结束"`
	Limit     int    `json:"limit"     p:"limit"     dc:"返回条数上限，默认 100"`
}

// DeviceHistoryFilterRes 筛选历史记录响应。
type DeviceHistoryFilterRes struct {
	List []entity.History `json:"list"`
}
'''

    # 在 DeviceHistoryPieceRes 之后插入
    target = "// DeviceHistoryPieceRes 区段历史列表。\ntype DeviceHistoryPieceRes struct {\n\tList []entity.History `json:\"list\"`\n}"
    replacement = target + new_code

    if new_code.strip() in content:
        print("[跳过] Filter 模型已存在")
        return

    content = content.replace(target, replacement)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[完成] 新增 Filter 模型定义")


def add_contract_method():
    """在 DeviceHistoryContract 中新增 ListHistoryFilter 方法声明"""
    file_path = os.path.join(GO_PROJECT_DIR, r"internal\services\contracts\runtime_contracts.go")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "ListHistoryFilter" in content:
        print("[跳过] ListHistoryFilter 方法已存在")
        return

    # 在 DeleteHistory 方法后插入
    target = "DeleteHistory(ctx context.Context, id int64, deviceNo string) error"
    replacement = target + "\n\tListHistoryFilter(ctx context.Context, deviceNo string, eventIds []int64, startTimeUnixSec, endTimeUnixSec int64, limit int) ([]entity.History, error)"

    content = content.replace(target, replacement)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[完成] 新增 ListHistoryFilter 契约方法")


def add_service_impl():
    """新增 filter.go 实现文件"""
    file_path = os.path.join(GO_PROJECT_DIR, r"internal\services\history\filter.go")
    if os.path.exists(file_path):
        print("[跳过] filter.go 已存在")
        return

    code = '''package history

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"hello/internal/dao"
	"hello/internal/model/entity"
	"hello/internal/platform/cachekit"

	"github.com/gogf/gf/v2/os/glog"
)

const filterListCacheTTL = 60 * time.Second

var filterCache = cachekit.Default()

// ListHistoryFilter 多条件筛选历史记录（多事件ID + 时间范围）。
// eventIds 为空则查询所有事件类型；startTime/endTime 为 0 表示不限制。
func ListHistoryFilter(ctx context.Context, deviceNo string, eventIds []int64, startTimeUnixSec, endTimeUnixSec int64, limit int) ([]entity.History, error) {
	deviceNo = strings.TrimSpace(deviceNo)
	if deviceNo == "" {
		return nil, fmt.Errorf("deviceNo 不能为空")
	}
	if limit <= 0 {
		limit = 100
	}
	if limit > 500 {
		limit = 500
	}

	ver := pieceCacheEpoch(ctx, deviceNo)
	eventIdsKey := strings.Trim(strings.Join(strings.Fields(fmt.Sprint(eventIds)), ","), "[]")
	cacheKey := cachekit.HistoryFilterDataKey(deviceNo, eventIdsKey, startTimeUnixSec, endTimeUnixSec, limit, ver)
	if raw, ok, err := filterCache.Get(ctx, cacheKey); err == nil && ok && raw != "" {
		var cached []entity.History
		if err := json.Unmarshal([]byte(raw), &cached); err == nil {
			return cached, nil
		}
	}

	model := dao.History.Ctx(ctx).
		Fields(historyListSelectFields()...).
		Where(dao.History.Columns().DeviceNo, deviceNo)

	if len(eventIds) > 0 {
		model = model.WhereIn(dao.History.Columns().EventId, eventIds)
	}

	stCol := dao.History.Columns().StartTime
	if startTimeUnixSec > 0 {
		model = model.Where(stCol+" >= ?", startTimeUnixSec)
	}
	if endTimeUnixSec > 0 {
		model = model.Where(stCol+" <= ?", endTimeUnixSec)
	}

	rows, err := model.
		OrderAsc(dao.History.Columns().Id).
		Limit(limit).
		All()
	if err != nil {
		return nil, err
	}

	out := make([]entity.History, 0, len(rows))
	for _, row := range rows {
		out = append(out, historyRowToEntity(row))
	}

	if blob, err := json.Marshal(out); err == nil {
		if err2 := filterCache.SetEX(ctx, cacheKey, string(blob), filterListCacheTTL); err2 != nil {
			glog.Warningf(ctx, "[history-filter] 写缓存失败 key=%s err=%v", cacheKey, err2)
		}
	}

	return out, nil
}

// historyFilterEventIdsToKey 将事件ID数组转换为缓存键字符串
func historyFilterEventIdsToKey(eventIds []int64) string {
	if len(eventIds) == 0 {
		return "all"
	}
	strs := make([]string, len(eventIds))
	for i, id := range eventIds {
		strs[i] = strconv.FormatInt(id, 10)
	}
	return strings.Join(strs, "-")
}
'''

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)
    print("[完成] 新增 filter.go 服务实现")


def add_filter_cache_key():
    """在 cachekit 中新增 HistoryFilterDataKey 函数"""
    file_path = os.path.join(GO_PROJECT_DIR, r"internal\platform\cachekit\keys.go")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "HistoryFilterDataKey" in content:
        print("[跳过] HistoryFilterDataKey 已存在")
        return

    # 找一个合适的位置插入
    new_func = '''
// HistoryFilterDataKey 生成历史筛选缓存键。
func HistoryFilterDataKey(deviceNo string, eventIdsKey string, startTime, endTime int64, limit int, ver int64) string {
	return fmt.Sprintf("history:filter:%s:%s:%d-%d:%d:%d", deviceNo, eventIdsKey, startTime, endTime, limit, ver)
}
'''

    # 在 HistoryPieceDataKey 函数后插入
    target = "func HistoryPieceDataKey(deviceNo string, eventID int64, startTime, endTime int64, ver int64) string {"
    if target in content:
        # 找到函数结束位置
        idx = content.find(target)
        end_idx = content.find("}", idx)
        if end_idx > 0:
            end_idx += 1
            content = content[:end_idx] + new_func + content[end_idx:]
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("[完成] 新增 HistoryFilterDataKey 缓存键函数")
            return

    print("[警告] 未找到 HistoryPieceDataKey，跳过缓存键添加")


def add_controller_method():
    """在 device_history.go controller 中新增 Filter 方法"""
    file_path = os.path.join(GO_PROJECT_DIR, r"internal\controller\device_history.go")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "func (c *HistoryCtrl) Filter(" in content:
        print("[跳过] Filter 方法已存在")
        return

    # 在 Piece 方法后插入 Filter 方法
    new_method = '''
// Filter 多条件筛选历史记录（多事件ID + 时间范围）。
// eventIds 为逗号分隔的事件ID列表；为空表示全部事件。
func (c *HistoryCtrl) Filter(ctx context.Context, req *v1.DeviceHistoryFilterReq) (res *v1.DeviceHistoryFilterRes, err error) {
	deviceNo := strings.TrimSpace(req.DeviceNo)
	if deviceNo == "" {
		return nil, gerror.NewCode(gcode.CodeInvalidParameter, "deviceNo 不能为空")
	}

	var eventIds []int64
	eventIdsStr := strings.TrimSpace(req.EventIds)
	if eventIdsStr != "" {
		for _, s := range strings.Split(eventIdsStr, ",") {
			s = strings.TrimSpace(s)
			if s == "" {
				continue
			}
			id, err := strconv.ParseInt(s, 10, 64)
			if err != nil || id <= 0 {
				continue
			}
			eventIds = append(eventIds, id)
		}
	}

	list, err := c.Svc.ListHistoryFilter(ctx, deviceNo, eventIds, req.StartTime, req.EndTime, req.Limit)
	if err != nil {
		return nil, err
	}
	return &v1.DeviceHistoryFilterRes{List: list}, nil
}
'''

    # 找到 Piece 方法的结束位置
    target = 'func (c *HistoryCtrl) Piece(ctx context.Context, req *v1.DeviceHistoryPieceReq) (res *v1.DeviceHistoryPieceRes, err error) {'
    if target in content:
        idx = content.find(target)
        # 找到这个函数的结束（下一个函数前）
        next_func = content.find("func (c *HistoryCtrl) ", idx + len(target))
        if next_func > 0:
            content = content[:next_func] + new_method + "\n" + content[next_func:]
        else:
            content += new_method

        # 需要确保导入了 strconv
        if '"strconv"' not in content:
            content = content.replace('"strings"', '"strconv"\n\t"strings"')

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("[完成] 新增 Filter controller 方法")
    else:
        print("[警告] 未找到 Piece 方法，跳过 Filter 方法添加")


def add_service_adapter():
    """在 history service 适配器中实现 ListHistoryFilter 方法"""
    # 找实现 DeviceHistoryContract 的结构体
    impl_file = os.path.join(GO_PROJECT_DIR, r"internal\services\history\service.go")
    if not os.path.exists(impl_file):
        print("[跳过] 未找到 service.go，假设 ListHistoryFilter 为包级函数")
        return

    with open(impl_file, "r", encoding="utf-8") as f:
        content = f.read()

    if "ListHistoryFilter" in content:
        print("[跳过] ListHistoryFilter 适配器已存在")
        return

    # 找 DeleteHistory 方法后插入
    target = "func (s *historyService) DeleteHistory(ctx context.Context, id int64, deviceNo string) error {"
    if target in content:
        idx = content.find(target)
        # 找到函数结束
        brace_count = 0
        end_idx = idx
        for i in range(idx, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break

        new_method = '''
func (s *historyService) ListHistoryFilter(ctx context.Context, deviceNo string, eventIds []int64, startTimeUnixSec, endTimeUnixSec int64, limit int) ([]entity.History, error) {
	return ListHistoryFilter(ctx, deviceNo, eventIds, startTimeUnixSec, endTimeUnixSec, limit)
}
'''
        content = content[:end_idx] + new_method + content[end_idx:]
        with open(impl_file, "w", encoding="utf-8") as f:
            f.write(content)
        print("[完成] 新增 ListHistoryFilter 适配器方法")
    else:
        print("[警告] 未找到 DeleteHistory 适配器方法，跳过")


def main():
    print("=== 开始修改 Go 侧 Filter API ===")
    add_filter_model()
    add_contract_method()
    add_service_impl()
    add_filter_cache_key()
    add_service_adapter()
    add_controller_method()
    print("=== Go 侧 Filter API 修改完成 ===")


if __name__ == "__main__":
    main()
