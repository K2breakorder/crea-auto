#!/usr/bin/env python3
"""セッション開始時に、今日の日付と直近の学び（learnings.md の最後の15行）を Claude に渡す。
「毎回クオリティを上げる」ための仕組み。"""
import datetime
import json
import os

root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
path = os.path.join(root, "knowledge", "learnings.md")
tail = ""
try:
    with open(path, encoding="utf-8") as f:
        lines = [l.rstrip() for l in f if l.strip().startswith("-")]
    tail = "\n".join(lines[-15:])
except OSError:
    pass

today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d (%a)")
ctx = (
    f"今日は {today}（日本時間）。投稿を作る前に /crea-latest-check で最新の仕様と広告ルールを確認すること。\n"
    "直近の学び（前回より1つ以上良くする）:\n" + (tail or "- （まだ記録なし）")
)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}, ensure_ascii=False))
