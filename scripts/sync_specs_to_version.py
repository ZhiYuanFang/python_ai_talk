#!/usr/bin/env python3
"""Merge OpenSpec change deltas into a versioned baseline (e.g. v0.0.1.md).

Workflow (project convention):
- Start from the latest version baseline under openspec/specs/v*.md
- Apply all delta specs under openspec/changes/<change>/specs/
- Write openspec/specs/<target-version>.md
- Optionally remove absorbed change directories (no openspec/changes/archive/)
"""
from __future__ import annotations

import argparse
import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


REQ_HEADER = re.compile(r"^### Requirement:(.*)$", re.MULTILINE)
SECTION_HEADER = re.compile(r"^## (ADDED|MODIFIED|REMOVED) Requirements\s*$", re.MULTILINE)
CAP_ANCHOR = re.compile(r'<a id="capability-([^"]+)"></a>')
CAP_TITLE = re.compile(r"^# Capability: (.+)\s*$", re.MULTILINE)


@dataclass
class Delta:
    added: dict[str, str] = field(default_factory=dict)
    modified: dict[str, str] = field(default_factory=dict)
    removed: set[str] = field(default_factory=set)


def _normalize_title(title: str) -> str:
    return " ".join(title.strip().split())


def _parse_requirement_blocks(section_text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    matches = list(REQ_HEADER.finditer(section_text))
    for i, match in enumerate(matches):
        title = _normalize_title(match.group(1))
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_text)
        blocks[title] = section_text[start:end].rstrip() + "\n"
    return blocks


def _parse_delta(text: str) -> Delta:
    delta = Delta()
    sections = list(SECTION_HEADER.finditer(text))
    for i, match in enumerate(sections):
        kind = match.group(1)
        start = match.end()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(text)
        body = text[start:end]
        blocks = _parse_requirement_blocks(body)
        if kind == "ADDED":
            delta.added.update(blocks)
        elif kind == "MODIFIED":
            delta.modified.update(blocks)
        elif kind == "REMOVED":
            delta.removed.update(blocks.keys())
    return delta


def _parse_capabilities(baseline_text: str) -> dict[str, str]:
    caps: dict[str, str] = {}
    anchors = list(CAP_ANCHOR.finditer(baseline_text))
    for i, match in enumerate(anchors):
        name = match.group(1)
        start = match.start()
        end = anchors[i + 1].start() if i + 1 < len(anchors) else baseline_text.rfind("\n---\n")
        if end == -1:
            end = len(baseline_text)
        caps[name] = baseline_text[start:end].strip()
    return caps


def _capability_requirements(cap_text: str) -> dict[str, str]:
    body = cap_text
    title_match = CAP_TITLE.search(body)
    if title_match:
        body = body[title_match.end() :]
    # Drop duplicate headers / source comments before first requirement section.
    first_req = REQ_HEADER.search(body)
    if first_req:
        body = body[first_req.start() :]
    return _parse_requirement_blocks(body)


def _render_capability(name: str, requirements: dict[str, str]) -> str:
    lines = [
        f'<a id="capability-{name}"></a>',
        "",
        f"# Capability: {name}",
        "",
        f"<!-- source: openspec/specs/{name}/spec.md -->",
        "",
        "## ADDED Requirements",
        "",
    ]
    for block in requirements.values():
        lines.append(block.rstrip())
        lines.append("")
    return "\n".join(lines).rstrip()


def _apply_delta(requirements: dict[str, str], delta: Delta) -> dict[str, str]:
    merged = dict(requirements)
    for title in delta.removed:
        merged.pop(title, None)
    for title, block in delta.modified.items():
        merged[title] = block
    for title, block in delta.added.items():
        merged[title] = block
    return merged


def _find_latest_baseline(specs_dir: Path) -> Path:
    versions = sorted(specs_dir.glob("v*.md"), key=lambda p: p.name)
    if not versions:
        raise SystemExit(f"No baseline found under {specs_dir}")
    return versions[-1]


def _collect_deltas(changes_dir: Path) -> list[tuple[str, Path, Path]]:
    items: list[tuple[str, Path, Path]] = []
    for change_dir in sorted(changes_dir.iterdir()):
        if not change_dir.is_dir() or change_dir.name == "archive":
            continue
        specs_root = change_dir / "specs"
        if not specs_root.is_dir():
            continue
        for spec_path in sorted(specs_root.rglob("spec.md")):
            cap = spec_path.parent.name
            items.append((change_dir.name, cap, spec_path))
    return items


def _change_order(changes_dir: Path) -> dict[str, float]:
    order: dict[str, float] = {}
    for change_dir in changes_dir.iterdir():
        if change_dir.is_dir() and change_dir.name != "archive":
            order[change_dir.name] = change_dir.stat().st_mtime
    return order


def sync_to_version(
    repo_root: Path,
    target_version: str,
    base_version: str | None = None,
    remove_changes: bool = False,
) -> None:
    specs_dir = repo_root / "openspec" / "specs"
    changes_dir = repo_root / "openspec" / "changes"
    specs_dir.mkdir(parents=True, exist_ok=True)

    if base_version:
        base_path = specs_dir / f"{base_version}.md"
    else:
        existing = list(specs_dir.glob("v*.md"))
        if existing:
            base_path = _find_latest_baseline(specs_dir)
        else:
            # 首次收版：无基线时从空能力集起步
            base_path = specs_dir / "_empty_base.md"
            base_path.write_text(
                "# Python AI Talk OpenSpec 空基线\n\n## 目录\n\n---\n",
                encoding="utf-8",
            )

    if not base_path.is_file():
        raise SystemExit(f"Baseline not found: {base_path}")

    baseline_text = base_path.read_text(encoding="utf-8")
    capabilities = _parse_capabilities(baseline_text)

    deltas = _collect_deltas(changes_dir)
    order = _change_order(changes_dir)
    deltas.sort(key=lambda item: (order.get(item[0], 0.0), item[0], item[1]))

    applied: list[str] = []
    for change_name, cap_name, spec_path in deltas:
        delta = _parse_delta(spec_path.read_text(encoding="utf-8"))
        if not (delta.added or delta.modified or delta.removed):
            continue
        existing = _capability_requirements(capabilities.get(cap_name, ""))
        merged = _apply_delta(existing, delta)
        capabilities[cap_name] = _render_capability(cap_name, merged)
        applied.append(f"{change_name}/{cap_name}")

    header = [
        f"# Python AI Talk OpenSpec 基线 {target_version}",
        "",
        f"> 由 `{base_path.name}` 合并 **{len(applied)}** 条 change delta 生成，共 **{len(capabilities)}** 个 capability。",
        f"> 生成日期：{date.today().isoformat()}",
        "",
        "## 目录",
        "",
    ]
    for name in sorted(capabilities):
        header.append(f"- [{name}](#capability-{name})")
    header.extend(["", "---", ""])

    body_parts = [
        _render_capability(name, _capability_requirements(capabilities[name]))
        for name in sorted(capabilities)
    ]
    out_path = specs_dir / f"{target_version}.md"
    out_text = "\n".join(header) + "\n" + "\n---\n\n".join(body_parts) + "\n\n---\n"
    out_path.write_text(out_text, encoding="utf-8")
    print(
        f"Wrote {out_path} ({out_path.stat().st_size:,} bytes, "
        f"{len(capabilities)} capabilities, {len(applied)} deltas)"
    )

    # 清理首次收版临时空基线文件
    empty_seed = specs_dir / "_empty_base.md"
    if empty_seed.is_file() and empty_seed.resolve() == base_path.resolve():
        empty_seed.unlink()
        print(f"Removed temporary seed {empty_seed.name}")

    if remove_changes:
        removed_dirs: list[str] = []
        for change_dir in sorted(changes_dir.iterdir()):
            if not change_dir.is_dir() or change_dir.name == "archive":
                continue
            shutil.rmtree(change_dir)
            removed_dirs.append(change_dir.name)
        print(f"Removed {len(removed_dirs)} change directories (no archive/):")
        for name in removed_dirs:
            print(f"  - {name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync OpenSpec change deltas into a version baseline."
    )
    parser.add_argument("version", help="Target version label, e.g. v0.0.1")
    parser.add_argument(
        "--base",
        help="Base version file name without path, e.g. v0.0.0 (default: latest v*.md)",
    )
    parser.add_argument(
        "--remove-changes",
        action="store_true",
        help="Delete openspec/changes/* after sync (project default; no archive/)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    version = args.version if args.version.startswith("v") else f"v{args.version}"
    sync_to_version(
        repo_root=repo_root,
        target_version=version,
        base_version=args.base,
        remove_changes=args.remove_changes,
    )


if __name__ == "__main__":
    main()
