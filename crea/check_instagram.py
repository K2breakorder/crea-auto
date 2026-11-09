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

# Googleビジネスプロフィール（読み取りのみ。投稿はしない）
gid, gsec, grt = os.environ.get("GBP_CLIENT_ID", ""), os.environ.get("GBP_CLIENT_SECRET", ""), os.environ.get("GBP_REFRESH_TOKEN", "")
gacc, gloc = os.environ.get("GBP_ACCOUNT_ID", ""), os.environ.get("GBP_LOCATION_ID", "")
if gid and gsec and grt:
    print("\n== Google 登録値の形式:", {"id_ok": gid.endswith(".apps.googleusercontent.com"), "secret_head": gsec[:7], "secret_len": len(gsec), "token_head": grt[:4], "token_len": len(grt), "空白や引用符": any(c in gsec + grt for c in " \t\n\"'")})
    r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "client_id": gid, "client_secret": gsec, "refresh_token": grt, "grant_type": "refresh_token"})
    print(f"\n== Google ログイン: HTTP {r.status_code}\n" + (str({k: v for k, v in r.json().items() if k in ("error", "error_description")}) if r.headers.get("content-type", "").startswith("application/json") else r.text[:200]))
    if r.ok:
        at = r.json()["access_token"]
        h = {"Authorization": f"Bearer {at}"}
        for name, url in [("Google 店舗情報", f"https://mybusinessbusinessinformation.googleapis.com/v1/locations/{gloc}?readMask=name,title"),
                          ("Google 投稿一覧（最新1件）", f"https://mybusiness.googleapis.com/v4/accounts/{gacc}/locations/{gloc}/localPosts?pageSize=1")]:
            x = requests.get(url, headers=h, timeout=30)
            print(f"\n== {name}: HTTP {x.status_code}\n" + x.text.replace(at, "***")[:500])
else:
    print("\n== Google: 未登録の項目があります", {"CLIENT_ID": bool(gid), "SECRET": bool(gsec), "REFRESH_TOKEN": bool(grt)})
