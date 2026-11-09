#!/usr/bin/env python3
"""APIキーやトークンをファイル・コマンドに書き込むのを止める（PreToolUse フック）。"""
import json
import re
import sys

PATTERNS = [
    (r"sk-ant-[A-Za-z0-9_\-]{20,}", "Anthropic APIキー"),
    (r"sk-[A-Za-z0-9]{32,}", "APIキー"),
    (r"ghp_[A-Za-z0-9]{30,}", "GitHubトークン"),
    (r"github_pat_[A-Za-z0-9_]{30,}", "GitHubトークン"),
    (r"AIza[0-9A-Za-z_\-]{35}", "Google APIキー"),
    (r"EAA[A-Za-z0-9]{60,}", "Meta(Instagram/Threads)トークン"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "秘密鍵"),
    (r"(?i)channel_?access_?token\s*[:=]\s*['\"]?[A-Za-z0-9+/=]{40,}", "LINEチャネルアクセストークン"),
]
BLOCKED_FILES = re.compile(r"(^|/)\.env(\.|$)")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    if tool in ("Write", "Edit"):
        path = ti.get("file_path", "")
        text = ti.get("content", "") + ti.get("new_string", "")
        if BLOCKED_FILES.search(path.replace("\\", "/")):
            print("[安全] .env への書き込みは止めました。鍵は GitHub Secrets に登録してください。", file=sys.stderr)
            return 2
    elif tool == "Bash":
        text = ti.get("command", "")
    else:
        return 0
    for pat, name in PATTERNS:
        if re.search(pat, text):
            print(f"[安全] {name}らしき文字列が含まれていたので止めました。鍵は GitHub Secrets に入れ、コードからは環境変数で読んでください。", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
