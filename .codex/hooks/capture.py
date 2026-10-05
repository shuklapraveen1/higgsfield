import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def safe_session_id(value):
    return re.sub(r"[^A-Za-z0-9_-]", "_", value or "unknown")


def main():
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    event = json.load(sys.stdin)
    event_name = event.get("hook_event_name")
    prompt = event.get("prompt") if event_name == "UserPromptSubmit" else None
    response = event.get("last_assistant_message") if event_name == "Stop" else None
    if prompt is None and response is None:
        return

    root = Path(__file__).resolve().parents[2]
    log_dir = root / ".agent-logs"
    log_dir.mkdir(exist_ok=True)
    session_id = safe_session_id(event.get("session_id"))
    timestamp = utc_now()
    model = event.get("model") or "unknown"
    candidates = sorted(log_dir.glob(f"*_{session_id}.md"), key=lambda p: p.name)
    log_path = candidates[-1] if candidates else log_dir / f"{timestamp[:19].replace(':', '-')}_{session_id}.md"

    if prompt is not None:
        if not log_path.exists():
            header = (
                "---\n"
                f"session_id: {session_id}\n"
                f"date: {timestamp[:10]}\n"
                "author: unknown\n"
                f"model: {model}\n"
                "tool: codex-cli\n"
                f"project: {root.name}\n"
                "total_exchanges: pending\n"
                f"first_prompt_time: {timestamp}\n"
                f"last_prompt_time: {timestamp}\n"
                "---\n\n"
                f"# Session Log - {timestamp[:10]}\n\n"
                f"Session: `{session_id[:8]}` | Project: `{root.name}` | Author: `unknown`\n\n"
                "---\n\n"
            )
            log_path.write_text(header, encoding="utf-8")
            exchange = 1
        else:
            existing = log_path.read_text(encoding="utf-8")
            exchange = existing.count("[LOG_ENTRY type=PROMPT ") + 1
            updated = re.sub(r"(?m)^last_prompt_time: .*?$", f"last_prompt_time: {timestamp}", existing, count=1)
            log_path.write_text(updated, encoding="utf-8", newline="")
        entry = (
            f"[LOG_ENTRY type=PROMPT num={exchange} session={session_id}]\n"
            f"timestamp: {timestamp}\n"
            f"model: {model}\n\n"
            f"{prompt}\n\n"
        )
        with log_path.open("a", encoding="utf-8", newline="") as f:
            f.write(entry)
    else:
        if not candidates:
            return
        log_path = candidates[-1]
        existing = log_path.read_text(encoding="utf-8")
        exchange = existing.count("[LOG_ENTRY type=PROMPT ")
        entry = (
            f"[LOG_ENTRY type=RESPONSE num={exchange} session={session_id}]\n"
            f"timestamp: {timestamp}\n"
            f"model: {model}\n\n"
            f"{response or ''}\n\n"
        )
        with log_path.open("a", encoding="utf-8", newline="") as f:
            f.write(entry)
        updated = log_path.read_text(encoding="utf-8")
        updated = re.sub(r"(?m)^total_exchanges: .*?$", f"total_exchanges: {exchange}", updated, count=1)
        updated = re.sub(r"(?m)^last_prompt_time: .*?$", f"last_prompt_time: {timestamp}", updated, count=1)
        log_path.write_text(updated, encoding="utf-8", newline="")


if __name__ == "__main__":
    main()
