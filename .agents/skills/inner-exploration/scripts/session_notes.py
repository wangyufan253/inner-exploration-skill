#!/usr/bin/env python3
"""Create, list, validate, and close local Markdown session summaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


REQUIRED_HEADINGS = (
    "## 本次焦点",
    "## 用户确认的事实",
    "## 感受与需要",
    "## 暂定理解",
    "## 用户认可的发现",
    "## 开放问题",
    "## 偏好与边界",
    "## 下次入口",
)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def default_root() -> Path:
    return Path.cwd() / ".inner-exploration" / "sessions"


def resolve_root(raw: Optional[str]) -> Path:
    root = Path(raw).expanduser() if raw else default_root()
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def session_path(root: Path, session_id: str) -> Path:
    if Path(session_id).name != session_id or not session_id.endswith(".md"):
        raise ValueError("session id must be a Markdown filename, not a path")
    path = (root / session_id).resolve()
    if path.parent != root:
        raise ValueError("session path escapes the configured root")
    return path


def template(title: str, timestamp: str) -> str:
    quoted_title = json.dumps(title, ensure_ascii=False)
    return f"""---
title: {quoted_title}
created_at: {timestamp}
updated_at: {timestamp}
status: active
privacy: local-summary-only
---

# {title}

## 本次焦点

待填写。

## 用户确认的事实

- 待填写。

## 感受与需要

- 待填写。

## 暂定理解

- 待核对；不要写成诊断或确定结论。

## 用户认可的发现

- 待填写。

## 开放问题

- 待填写。

## 偏好与边界

- 待填写。

## 下次入口

待填写。
"""


def metadata(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    if not match:
        return ""
    value = match.group(1).strip()
    if value.startswith('"'):
        try:
            return str(json.loads(value))
        except json.JSONDecodeError:
            pass
    return value


def create(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    timestamp = now_iso()
    day = timestamp[:10]
    digest = hashlib.sha256(args.title.encode("utf-8")).hexdigest()[:8]
    path = session_path(root, f"{day}--{digest}.md")
    if not path.exists():
        path.write_text(template(args.title, timestamp), encoding="utf-8")
    print(path)
    return 0


def list_sessions(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    for path in sorted(root.glob("*.md"), reverse=True):
        text = path.read_text(encoding="utf-8")
        print(
            "\t".join(
                (
                    path.name,
                    metadata(text, "status") or "unknown",
                    metadata(text, "updated_at") or "unknown",
                    metadata(text, "title") or path.stem,
                )
            )
        )
    return 0


def validate(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    path = session_path(root, args.id)
    if not path.is_file():
        print(f"missing session: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    if missing:
        print("missing headings: " + ", ".join(missing), file=sys.stderr)
        return 1
    for key in ("title", "created_at", "updated_at", "status", "privacy"):
        if not metadata(text, key):
            print(f"missing metadata: {key}", file=sys.stderr)
            return 1
    print(f"valid: {path}")
    return 0


def close(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    path = session_path(root, args.id)
    if not path.is_file():
        print(f"missing session: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")
    text, count = re.subn(r"^status:\s*.+$", "status: closed", text, count=1, flags=re.MULTILINE)
    if count != 1:
        print("missing status metadata", file=sys.stderr)
        return 1
    text, count = re.subn(
        r"^updated_at:\s*.+$",
        f"updated_at: {now_iso()}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        print("missing updated_at metadata", file=sys.stderr)
        return 1
    path.write_text(text, encoding="utf-8")
    print(path)
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="create or reuse a session template")
    create_parser.add_argument("--title", required=True)
    create_parser.add_argument("--root")
    create_parser.set_defaults(handler=create)

    list_parser = subparsers.add_parser("list", help="list local session summaries")
    list_parser.add_argument("--root")
    list_parser.set_defaults(handler=list_sessions)

    validate_parser = subparsers.add_parser("validate", help="validate a session summary")
    validate_parser.add_argument("--id", required=True)
    validate_parser.add_argument("--root")
    validate_parser.set_defaults(handler=validate)

    close_parser = subparsers.add_parser("close", help="mark a session as closed")
    close_parser.add_argument("--id", required=True)
    close_parser.add_argument("--root")
    close_parser.set_defaults(handler=close)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.handler(args))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
