"""Instagram接続テスト（投稿はしない）：アカウント情報と投稿枠を読み取れるか確認する"""
import os, requests

V = os.environ.get("IG_API_VERSION", "v23.0")
HOST = os.environ.get("IG_API_HOST") or "graph.facebook.com"
tok = os.environ.get("IG_ACCESS_TOKEN", "")
iid = os.environ.get("IG_USER_ID", "")
print("トークン長さ:", len(tok), "/ IG_USER_ID:", iid)

for name, path, params in [
    ("アカウント情報", f"{iid}", {"fields": "id,username,name,media_count,followers_count"}),
    ("投稿枠（24時間）", f"{iid}/content_publishing_limit", {"fields": "quota_usage,config"}),
]:
    r = requests.get(f"https://{HOST}/{V}/{path}", params=dict(params, access_token=tok), timeout=30)
    print(f"\n== {name}: HTTP {r.status_code}\n" + r.text.replace(tok, "***")[:600])
