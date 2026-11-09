#!/usr/bin/env python3
"""保存した投稿を crea/compliance.py で法規チェックする（PostToolUse フック）。

対象:
  - posts/<媒体>/*.md|*.txt      … 手で作った単発の投稿
  - data/queue/week-*.json        … 自動生成された予約投稿（status が pending のもの）
NG があれば exit 2 → Claude に書き直させる。
"""
import json
import os
import sys

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
try:
    from crea.compliance import check  # 唯一のNG語リスト
except Exception as e:  # compliance が読めない時は止めずに知らせる
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
          "additionalContext": f"[広告チェック] crea/compliance.py を読み込めませんでした: {e}"}}, ensure_ascii=False))
    sys.exit(0)

FOLDER_TO_CHANNEL = {"gmap": "gbp", "gbp": "gbp", "hpb": "hpb_blog", "instagram": "instagram",
                     "threads": "threads", "line": "line_broadcast"}


def fmt(label, issues):
    seen, lines = set(), []
    for i in issues:
        key = (i["category"], i["word"])
        if key not in seen:
            seen.add(key)
            lines.append(f"  - {i['category']}：「{i['word']}」")
    return f"{label}\n" + "\n".join(lines)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    path = (data.get("tool_input") or {}).get("file_path", "")
    rel = os.path.relpath(os.path.abspath(path), ROOT).replace("\\", "/")
    parts = rel.split("/")
    reports = []

    if parts[0] == "posts" and len(parts) >= 3 and rel.endswith((".md", ".txt")):
        channel = FOLDER_TO_CHANNEL.get(parts[1])
        if not channel:
            return 0
        with open(path, encoding="utf-8") as f:
            issues = check(f.read(), channel)
        if issues:
            reports.append(fmt(os.path.basename(path), issues))

    elif rel.startswith("data/queue/") and rel.endswith(".json"):
        with open(path, encoding="utf-8") as f:
            q = json.load(f)
        for it in q.get("items", []):
            if it.get("status") != "pending":
                continue
            text = (it.get("title") or "") + "\n" + (it.get("text") or "")
            issues = check(text, it.get("channel", ""))
            if issues:
                reports.append(fmt(f"{it.get('id')}（{it.get('channel')}）", issues))
    else:
        return 0

    if reports:
        print("[広告チェックNG] crea/compliance.py に引っかかる表現があります。"
              "knowledge/regulations.md の言い換えで直してから、もう一度保存してください。\n"
              + "\n".join(reports), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
