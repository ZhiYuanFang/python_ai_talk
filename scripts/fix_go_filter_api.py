# -*- coding: utf-8 -*-
"""
补充修改 Go 侧 Filter API：缓存键、local/remote/switch 三个适配器
"""

import os

GO_PROJECT_DIR = r"d:\work\go_ai_talk"


def add_cache_key():
    """在 keys_history.go 中新增 HistoryFilterDataKey 函数"""
    file_path = os.path.join(GO_PROJECT_DIR, r"internal\platform\cachekit\keys_history.go")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "HistoryFilterDataKey" in content:
        print("[跳过] HistoryFilterDataKey 已存在")
        return

    new_const = 'const historyFilterDataPrefix = "history:filter:data:"\n'
    if new_const not in content:
        # 在 historyPieceDataPrefix 后插入
        target = 'const historyPieceDataPrefix = "history:piece:data:"'
        replacement = target + "\n" + new_const.strip()
        content = content.replace(target, replacement)

    new_func = '''
// HistoryFilterDataKey 按查询参数与版本 hash 的 filter 列表 JSON 缓存；TTL 60s。
func HistoryFilterDataKey(deviceNo string, eventIdsKey string, startTimeUnixSec, endTimeUnixSec int64, limit int, ver int64) string {
	sum := sha256.Sum256([]byte(fmt.Sprintf("%s|%s|%d|%d|%d|%d", deviceNo, eventIdsKey, startTimeUnixSec, endTimeUnixSec, limit, ver)))
	return historyFilterDataPrefix + hex.EncodeToString(sum[:16])
}
'''
    # 在 HistoryPieceDataKey 函数后插入
    target_end = "return historyPieceDataPrefix + hex.EncodeToString(sum[:16])\n}"
    if target_end in content:
        content = content.replace(target_end, target_end + new_func)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("[完成] 新增 HistoryFilterDataKey 缓存键函数")
    else:
        print("[警告] 未找到 HistoryPieceDataKey 结束位置")


def fix_filter_go_cache():
    """修复 filter.go 中的缓存键调用（使用 hash 版本）"""
    file_path = os.path.join(GO_PROJECT_DIR, r"internal\services\history\filter.go")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 修复：导入 sha256 和 hex
    if '"crypto/sha256"' not in content:
        content = content.replace('"encoding/json"', '"crypto/sha256"\n\t"encoding/hex"\n\t"encoding/json"')

    # 修复缓存键生成方式：使用 hash
    old_cache_key = 'eventIdsKey := strings.Trim(strings.Join(strings.Fields(fmt.Sprint(eventIds)), ","), "[]")\n\tcacheKey := cachekit.HistoryFilterDataKey(deviceNo, eventIdsKey, startTimeUnixSec, endTimeUnixSec, limit, ver)'
    new_cache_key = '''eventIdsKey := historyFilterEventIdsToKey(eventIds)
	cacheKey := cachekit.HistoryFilterDataKey(deviceNo, eventIdsKey, startTimeUnixSec, endTimeUnixSec, limit, ver)'''

    if old_cache_key in content:
        content = content.replace(old_cache_key, new_cache_key)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("[完成] 修复 filter.go 缓存键")
    else:
        print("[跳过] filter.go 缓存键已修复或格式不同")


def add_local_service_method():
    """在 local.go 中新增 ListHistoryFilter 方法"""
    file_path = os.path.join(GO_PROJECT_DIR, r"internal\services\history\local.go")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "func (s *localService) ListHistoryFilter" in content:
        print("[跳过] localService.ListHistoryFilter 已存在")
        return

    target = "func (s *localService) DeleteHistory(ctx context.Context, id int64, deviceNo string) error {\n\treturn DeleteDeviceHistory(ctx, id, deviceNo)\n}"
    if target in content:
        new_method = '''
func (s *localService) ListHistoryFilter(ctx context.Context, deviceNo string, eventIds []int64, startTimeUnixSec, endTimeUnixSec int64, limit int) ([]entity.History, error) {
	return ListHistoryFilter(ctx, deviceNo, eventIds, startTimeUnixSec, endTimeUnixSec, limit)
}
'''
        content = content.replace(target, target + new_method)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("[完成] 新增 localService.ListHistoryFilter")
    else:
        print("[警告] 未找到 localService.DeleteHistory")


def add_remote_client_method():
    """在 adapter.go 中新增 historyRemoteClient.ListHistoryFilter 方法"""
    file_path = os.path.join(GO_PROJECT_DIR, r"internal\services\history\adapter.go")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "func (r *historyRemoteClient) ListHistoryFilter" in content:
        print("[跳过] historyRemoteClient.ListHistoryFilter 已存在")
        return

    # 在 DeleteHistory 后插入
    target = '''func (r *historyRemoteClient) DeleteHistory(ctx context.Context, id int64, deviceNo string) error {
	if err := r.notReady(); err != nil {
		return err
	}
	t := r.targets
	return r.doJSON(ctx, http.MethodPost, r.historyBase, t.HistoryEventDeletePath(), nil, map[string]interface{}{"id": id, "deviceNo": strings.TrimSpace(deviceNo)}, nil)
}'''

    if target in content:
        new_method = '''
func (r *historyRemoteClient) ListHistoryFilter(ctx context.Context, deviceNo string, eventIds []int64, startTimeUnixSec, endTimeUnixSec int64, limit int) ([]entity.History, error) {
	if err := r.notReady(); err != nil {
		return nil, err
	}
	t := r.targets
	eventIdsStr := ""
	for i, id := range eventIds {
		if i > 0 {
			eventIdsStr += ","
		}
		eventIdsStr += strconv.FormatInt(id, 10)
	}
	params := url.Values{}
	params.Set("deviceNo", strings.TrimSpace(deviceNo))
	params.Set("eventIds", eventIdsStr)
	params.Set("startTime", strconv.FormatInt(startTimeUnixSec, 10))
	params.Set("endTime", strconv.FormatInt(endTimeUnixSec, 10))
	params.Set("limit", strconv.Itoa(limit))
	var res struct {
		List []entity.History `json:"list"`
	}
	if err := r.doJSON(ctx, http.MethodGet, r.historyBase, t.HistoryFilterPath()+"?"+params.Encode(), nil, nil, &res); err != nil {
		return nil, err
	}
	return res.List, nil
}
'''
        content = content.replace(target, target + new_method)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("[完成] 新增 historyRemoteClient.ListHistoryFilter")
    else:
        print("[警告] 未找到 historyRemoteClient.DeleteHistory")


def add_switch_adapter_method():
    """在 adapter.go 中新增 switchAdapter.ListHistoryFilter 方法"""
    file_path = os.path.join(GO_PROJECT_DIR, r"internal\services\history\adapter.go")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "func (a *switchAdapter) ListHistoryFilter" in content:
        print("[跳过] switchAdapter.ListHistoryFilter 已存在")
        return

    target = '''func (a *switchAdapter) DeleteHistory(ctx context.Context, id int64, deviceNo string) error {
	err := a.run(a.shouldUseRemote(deviceNo), func() error { return a.remote.DeleteHistory(ctx, id, deviceNo) }, func() error {
		return a.local.DeleteHistory(ctx, id, deviceNo)
	})
	if err == nil {
		historyCache.patchHistoryOnDelete(ctx, deviceNo, id)
	}
	return err
}'''

    if target in content:
        new_method = '''
func (a *switchAdapter) ListHistoryFilter(ctx context.Context, deviceNo string, eventIds []int64, startTimeUnixSec, endTimeUnixSec int64, limit int) ([]entity.History, error) {
	var out []entity.History
	err := a.run(a.shouldUseRemote(deviceNo), func() error {
		var err error
		out, err = a.remote.ListHistoryFilter(ctx, deviceNo, eventIds, startTimeUnixSec, endTimeUnixSec, limit)
		return err
	}, func() error {
		var err error
		out, err = a.local.ListHistoryFilter(ctx, deviceNo, eventIds, startTimeUnixSec, endTimeUnixSec, limit)
		return err
	})
	return out, err
}
'''
        content = content.replace(target, target + new_method)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("[完成] 新增 switchAdapter.ListHistoryFilter")
    else:
        print("[警告] 未找到 switchAdapter.DeleteHistory")


def add_http_target_path():
    """在 contracts.HTTPTargets 中新增 HistoryFilterPath 方法"""
    contracts_dir = os.path.join(GO_PROJECT_DIR, r"internal\services\contracts")
    # 找 HTTPTargets 定义的文件
    for fname in os.listdir(contracts_dir):
        if fname.endswith(".go"):
            fpath = os.path.join(contracts_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            if "type HTTPTargets struct" in content and "HistoryEventDeletePath" in content:
                if "HistoryFilterPath" in content:
                    print(f"[跳过] HistoryFilterPath 已存在于 {fname}")
                    return True
                # 添加 HistoryFilterPath 方法
                target = "func (h HTTPTargets) HistoryEventDeletePath() string {"
                if target in content:
                    new_method = '''
func (h HTTPTargets) HistoryFilterPath() string {
	return h.HistoryPrefix + "/api/filter"
}
'''
                    content = content.replace(target, new_method + "\n" + target)
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"[完成] 新增 HistoryFilterPath 方法于 {fname}")
                    return True
    print("[警告] 未找到 HTTPTargets 定义文件")
    return False


def main():
    print("=== 补充修改 Go 侧 Filter API ===")
    add_cache_key()
    fix_filter_go_cache()
    add_local_service_method()
    add_http_target_path()
    add_remote_client_method()
    add_switch_adapter_method()
    print("=== 补充修改完成 ===")


if __name__ == "__main__":
    main()
