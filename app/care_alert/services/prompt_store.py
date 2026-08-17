"""
护理留意全局 prompt / ledger 本地存储

业务说明：
从 Docker 挂载目录加载全局 prompt 投影（prompt.json）；缺失则 bootstrap 默认模板并写出。
月龄与历史不落盘，仅由运行时拼接进 user message。
飞轮重写对比样例时：文件锁 + 原子替换 + 可选 .bak；落盘前校验拒绝动态实例值。
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)

PROMPT_FILENAME = "prompt.json"
LEDGER_FILENAME = "ledger.jsonl"
META_FILENAME = "flywheel_meta.json"

# 进程内可重入写锁（同进程多协程；append 内会再写 meta）
_write_lock = threading.RLock()

# 禁止落盘的动态实例痕迹（兼容旧「近两日」与新「近期」标签）
_AGE_INSTANCE_RE = re.compile(r"宝宝月龄\s*[：:]\s*\d+")
_HISTORY_INSTANCE_RE = re.compile(
    r"(?:近两日|近期)记录[（(].*?[）)].*?[：:].*\S",
    re.DOTALL,
)

# prompt.json 文档版本：升级时覆盖 output_format，保留 contrastive_examples
PROMPT_DOC_VERSION = 3


def default_output_format() -> str:
    """
    默认输出格式与判定规则（静态，不含月龄/历史实例）。

    业务口径（v3 压缩）：
    - 政策唯一在本块；user 只注入实例
    - 有近期记录且对照表可用时 items 至少 1 条；弱信号可轻提
    - 必须结合月龄；未知不编造常模；窗口以运行时注入为准

    Returns:
        写入 prompt.json 的 output_format 文本
    """
    return """
你是一位专业的育儿专家，帮家长判断今天有没有「值得留意」的护理点。

【输出】只输出一个 JSON 对象（不要 Markdown 代码块，不要其它说明）：
{
  "items": [
    {
      "eventId": "对照表中的事件ID",
      "eventName": "事件中文名",
      "summaryLine": "跑马灯摘要约20字内",
      "followUpPrompt": "家长可原样发给陪伴树洞的口语追问",
      "reasons": [
        {
          "type": "elongatedInterval|longActive|suddenAbsence|其它短驼峰",
          "score": 0.0到1.0,
          "expectationUsed": true或false,
          "ageMonths": 月龄整数或省略,
          "medianGapMs": 毫秒或省略,
          "lastGapMs": 毫秒或省略,
          "expectGapMaxMs": 毫秒或省略,
          "p75DurMs": 毫秒或省略,
          "elapsedMs": 毫秒或省略,
          "expectDurMaxMs": 毫秒或省略,
          "dailyAvg": 数或省略,
          "recent48hCount": 整数或省略,
          "stillExpected": true/false或省略,
          "detailLines": ["可选中文补充"]
        }
      ]
    }
  ]
}
""".strip()


def default_prompt_document() -> Dict[str, Any]:
    """
    Bootstrap 默认 prompt 文档。

    业务逻辑：
    仅含静态块；contrastive_examples 初始为空；声明 runtime 注入字段由代码拼接。
    """
    return {
        "version": PROMPT_DOC_VERSION,
        "output_format": default_output_format(),
        "guidance": "",
        "contrastive_examples": "",
        "runtime_fields": [
            "baby_age_months",
            "history_block",
            "event_id_legend",
        ],
        "updated_at": int(time.time()),
    }


def prompt_dir() -> Path:
    """解析配置的 care_alert 数据目录。"""
    raw = (getattr(settings, "care_alert_prompt_dir", None) or "data/care_alert").strip()
    return Path(raw)


def prompt_path() -> Path:
    return prompt_dir() / PROMPT_FILENAME


def ledger_path() -> Path:
    return prompt_dir() / LEDGER_FILENAME


def meta_path() -> Path:
    return prompt_dir() / META_FILENAME


def ensure_dir() -> Path:
    """确保数据目录存在。"""
    d = prompt_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def validate_prompt_document(doc: Dict[str, Any]) -> Optional[str]:
    """
    校验落盘文档：结构完整且无动态实例值。

    Returns:
        None 表示合法；否则返回错误原因字符串
    """
    if not isinstance(doc, dict):
        return "prompt 文档不是对象"
    output_format = doc.get("output_format")
    if not isinstance(output_format, str) or not output_format.strip():
        return "output_format 缺失或为空"
    examples = doc.get("contrastive_examples")
    if examples is None:
        examples = ""
    if not isinstance(examples, str):
        return "contrastive_examples 必须是字符串"
    blob = f"{output_format}\n{examples}\n{doc.get('guidance') or ''}"
    if _AGE_INSTANCE_RE.search(blob):
        return "禁止落盘具体「宝宝月龄：N」实例"
    if _HISTORY_INSTANCE_RE.search(blob):
        return "禁止落盘近期/近两日历史流水实例"
    # 额外拦截常见「今天/昨天 HH:MM」流水痕迹（宽松）
    if re.search(r"(今天|昨天).{0,8}\d{1,2}:\d{2}", blob):
        return "禁止落盘含具体时刻的历史流水痕迹"
    max_chars = max(200, int(getattr(settings, "care_alert_examples_max_chars", 1200) or 1200))
    if len(examples) > max_chars:
        return f"contrastive_examples 超过上限 {max_chars}"
    return None


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    """原子写 JSON：临时文件 + replace；同目录保留 .bak。"""
    ensure_dir()
    text = json.dumps(data, ensure_ascii=False, indent=2)
    fd, tmp_name = tempfile.mkstemp(
        prefix="care_alert_prompt_",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            bak = path.with_suffix(path.suffix + ".bak")
            try:
                if bak.exists():
                    bak.unlink()
                path.replace(bak)
            except OSError as e:
                logger.warning("护理留意 prompt 备份失败: %s", e)
        Path(tmp_name).replace(path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _maybe_migrate_prompt_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    版本迁移：version < PROMPT_DOC_VERSION 时覆盖 output_format，保留 contrastive_examples。

    Args:
        doc: 已通过结构校验的文档

    Returns:
        迁移后的文档（可能已写盘）
    """
    try:
        ver = int(doc.get("version") or 1)
    except (TypeError, ValueError):
        ver = 1
    if ver >= PROMPT_DOC_VERSION:
        return doc

    migrated = dict(doc)
    # 保留飞轮样例与自定义 guidance；只升级静态判定口径
    migrated["output_format"] = default_output_format()
    migrated["version"] = PROMPT_DOC_VERSION
    migrated["runtime_fields"] = [
        "baby_age_months",
        "history_block",
        "event_id_legend",
    ]
    migrated["updated_at"] = int(time.time())
    err = validate_prompt_document(migrated)
    if err:
        logger.warning("护理留意 prompt 迁移后非法(%s)，跳过写盘仍返回内存迁移稿", err)
        return migrated
    try:
        _atomic_write_json(prompt_path(), migrated)
        logger.info(
            "护理留意 prompt 已迁移至 v%s（保留 contrastive_examples）",
            PROMPT_DOC_VERSION,
        )
    except Exception as e:
        logger.error("护理留意 prompt 迁移写盘失败: %s", e, exc_info=True)
    return migrated


def load_or_bootstrap_prompt() -> Dict[str, Any]:
    """
    加载 prompt.json；不存在或损坏则 bootstrap 并写出默认模板。
    低版本文档升级 output_format，保留已有对比样例。

    Returns:
        prompt 文档 dict
    """
    path = prompt_path()
    with _write_lock:
        if path.exists():
            try:
                raw = path.read_text(encoding="utf-8")
                doc = json.loads(raw)
                err = validate_prompt_document(doc)
                if err is None:
                    return _maybe_migrate_prompt_doc(doc)
                logger.warning("护理留意 prompt 非法(%s)，将 bootstrap 覆盖", err)
            except Exception as e:
                logger.warning("护理留意 prompt 读取失败，将 bootstrap: %s", e)
        doc = default_prompt_document()
        try:
            _atomic_write_json(path, doc)
            logger.info("护理留意 prompt 已 bootstrap: %s", path)
        except Exception as e:
            logger.error("护理留意 prompt bootstrap 写入失败: %s", e, exc_info=True)
        return doc


def save_prompt_document(doc: Dict[str, Any]) -> bool:
    """
    校验并原子写入 prompt.json。

    Returns:
        True 写入成功；False 校验失败或 IO 失败（保留旧文件）
    """
    err = validate_prompt_document(doc)
    if err:
        logger.warning("拒绝写入非法护理留意 prompt: %s", err)
        return False
    payload = dict(doc)
    payload["updated_at"] = int(time.time())
    if "version" not in payload:
        payload["version"] = 1
    with _write_lock:
        try:
            _atomic_write_json(prompt_path(), payload)
            logger.info("护理留意 prompt 已更新: %s", prompt_path())
            return True
        except Exception as e:
            logger.error("护理留意 prompt 写入失败: %s", e, exc_info=True)
            return False


def load_flywheel_meta() -> Dict[str, Any]:
    """读取飞轮元数据（上次重写时间、自上次以来新增条数）。"""
    path = meta_path()
    if not path.exists():
        return {"last_rewrite_at": 0, "entries_since_rewrite": 0}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception as e:
        logger.warning("护理留意飞轮 meta 读取失败: %s", e)
    return {"last_rewrite_at": 0, "entries_since_rewrite": 0}


def save_flywheel_meta(meta: Dict[str, Any]) -> None:
    """写入飞轮元数据。"""
    with _write_lock:
        try:
            ensure_dir()
            meta_path().write_text(
                json.dumps(meta, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("护理留意飞轮 meta 写入失败: %s", e)


def append_ledger_entry(entry: Dict[str, Any]) -> None:
    """
    追加一条 ledger.jsonl，并按上限滚动裁剪。

    Side Effects:
        更新 entries_since_rewrite 计数
    """
    ensure_dir()
    line = json.dumps(entry, ensure_ascii=False)
    with _write_lock:
        path = ledger_path()
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            logger.error("护理留意 ledger 追加失败: %s", e, exc_info=True)
            return

        max_lines = max(50, int(getattr(settings, "care_alert_ledger_max_lines", 500) or 500))
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) > max_lines:
                path.write_text("\n".join(lines[-max_lines:]) + "\n", encoding="utf-8")
        except Exception as e:
            logger.warning("护理留意 ledger 裁剪失败: %s", e)

        meta = load_flywheel_meta()
        meta["entries_since_rewrite"] = int(meta.get("entries_since_rewrite") or 0) + 1
        save_flywheel_meta(meta)


def read_ledger_entries(*, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """读取 ledger 条目（从旧到新）；损坏行跳过。"""
    path = ledger_path()
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    except Exception as e:
        logger.warning("护理留意 ledger 读取失败: %s", e)
        return []
    if limit is not None and limit > 0:
        return out[-limit:]
    return out


def build_system_prompt_from_doc(doc: Dict[str, Any]) -> str:
    """
    由落盘文档组装 system prompt（静态块 + 可选对比样例）。

    Args:
        doc: prompt.json 内容

    Returns:
        system 提示词
    """
    parts = [(doc.get("output_format") or "").strip()]
    guidance = (doc.get("guidance") or "").strip()
    if guidance:
        parts.append(guidance)
    examples = (doc.get("contrastive_examples") or "").strip()
    if examples:
        parts.append(examples)
    return "\n\n".join(p for p in parts if p)
