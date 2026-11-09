"""SNS接続テスト（投稿・配信はしない）：Instagram・Threads・LINEにつながるか確認する"""
import os, datetime as dt, requests

V = os.environ.get("IG_API_VERSION", "v23.0")
HOST = os.environ.get("IG_API_HOST") or "graph.facebook.com"
tok = os.environ.get("IG_ACCESS_TOKEN", "")
iid = os.environ.get("IG_USER_ID", "")
th = os.environ.get("THREADS_ACCESS_TOKEN", "")
line = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

def show(name, url, params, secret):
    r = requests.get(url, params=dict(params, access_token=secret), timeout=30)
    print(f"\n== {name}: HTTP {r.status_code}\n" + r.text.replace(secret, "***")[:600])

if tok and iid:
    show("Instagram アカウント", f"https://{HOST}/{V}/{iid}", {"fields": "id,username,followers_count"}, tok)
    show("Instagram 場所タグ用ページ", f"https://{HOST}/{V}/me/accounts", {"fields": "id,name,location,instagram_business_account"}, tok)
    show("Instagram 投稿枠", f"https://{HOST}/{V}/{iid}/content_publishing_limit", {"fields": "quota_usage,config"}, tok)
if th:
    show("Threads アカウント", "https://graph.threads.net/v1.0/me", {"fields": "id,username"}, th)
    show("Threads 投稿枠", "https://graph.threads.net/v1.0/me/threads_publishing_limit", {"fields": "quota_usage,config"}, th)
if line:
    h = {"Authorization": f"Bearer {line}"}
    day = (dt.date.today() - dt.timedelta(days=2)).strftime("%Y%m%d")
    for name, url in [("LINE アカウント", "https://api.line.me/v2/bot/info"),
                      ("LINE 月の通数上限", "https://api.line.me/v2/bot/message/quota"),
                      ("LINE 今月の使用通数", "https://api.line.me/v2/bot/message/quota/consumption"),
                      ("LINE 友だち数", f"https://api.line.me/v2/bot/insight/followers?date={day}")]:
        r = requests.get(url, headers=h, timeout=30)
        print(f"\n== {name}: HTTP {r.status_code}\n" + r.text.replace(line, "***")[:400])
