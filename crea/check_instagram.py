"""SNS接続テスト（投稿はしない）：Instagram・Threadsのアカウント情報と投稿枠を読み取れるか確認する"""
import os, requests

V = os.environ.get("IG_API_VERSION", "v23.0")
HOST = os.environ.get("IG_API_HOST") or "graph.facebook.com"
tok = os.environ.get("IG_ACCESS_TOKEN", "")
iid = os.environ.get("IG_USER_ID", "")
th = os.environ.get("THREADS_ACCESS_TOKEN", "")

def show(name, url, params, secret):
    r = requests.get(url, params=dict(params, access_token=secret), timeout=30)
    print(f"\n== {name}: HTTP {r.status_code}\n" + r.text.replace(secret, "***")[:600])

if tok and iid:
    show("Instagram アカウント", f"https://{HOST}/{V}/{iid}", {"fields": "id,username,followers_count"}, tok)
    show("Instagram 投稿枠", f"https://{HOST}/{V}/{iid}/content_publishing_limit", {"fields": "quota_usage,config"}, tok)
if th:
    show("Threads アカウント", "https://graph.threads.net/v1.0/me", {"fields": "id,username"}, th)
    show("Threads 投稿枠", "https://graph.threads.net/v1.0/me/threads_publishing_limit", {"fields": "quota_usage,config"}, th)
