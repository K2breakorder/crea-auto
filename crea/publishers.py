"""各媒体への投稿処理"""
import os, time, datetime as dt
import requests
from .common import DRY_RUN, image_public_url, notify, now

IG_VER = os.environ.get("IG_API_VERSION", "v23.0")
# Metaの統合ログイン（システムユーザートークン）は graph.facebook.com を使う
IG_HOST = os.environ.get("IG_API_HOST") or "graph.facebook.com"
T = 60


class MissingConfig(Exception):
    pass


def _env(name):
    v = os.environ.get(name)
    if not v:
        raise MissingConfig(f"GitHub Secrets に {name} がありません")
    return v


def _check(r):
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text[:500]}")
    return r.json() if r.text else {}


# ---------------- Instagram（統合ログイン／システムユーザートークン） ----------------
def ig_user_id(tok):
    """IG_USER_ID が未登録なら、トークンの許可情報からInstagramアカウントIDを自動で取り出す"""
    if os.environ.get("IG_USER_ID"):
        return os.environ["IG_USER_ID"]
    d = _check(requests.get(f"https://{IG_HOST}/{IG_VER}/debug_token", timeout=T,
                            params={"input_token": tok, "access_token": tok})).get("data", {})
    for sc in d.get("granular_scopes", []):
        if sc.get("scope") in ("instagram_content_publish", "instagram_basic") and sc.get("target_ids"):
            return sc["target_ids"][0]
    raise MissingConfig("InstagramアカウントIDを特定できません（IG_USER_ID を登録してください）")


def ig_location_id(tok, ig):
    """場所タグ用のID。IG_LOCATION_ID があればそれを使い、なければ
    Instagramとつながっている住所つきFacebookページのIDを自動で探す。見つからなければ None。"""
    v = os.environ.get("IG_LOCATION_ID")
    if not v:
        try:
            from .common import config
            v = str((config().get("clinic") or {}).get("ig_location_id") or "")
        except Exception:
            v = ""
    if v:
        return v
    try:
        r = requests.get(f"https://{IG_HOST}/{IG_VER}/me/accounts", timeout=T, params={
            "fields": "id,name,location,instagram_business_account", "access_token": tok})
        for pg in (r.json().get("data") or []):
            if (pg.get("instagram_business_account") or {}).get("id") == str(ig) and pg.get("location"):
                return pg["id"]
        print("場所タグ用のページが見つかりませんでした:", r.text[:300])
    except Exception as e:
        print("場所タグの確認に失敗:", e)
    return None


def post_instagram(item):
    url = image_public_url(item["image"])
    if DRY_RUN:
        return {"dry_run": True, "image_url": url}
    tok = _env("IG_ACCESS_TOKEN")
    ig = ig_user_id(tok)
    base = f"https://{IG_HOST}/{IG_VER}"
    data = {"image_url": url, "caption": item["text"], "access_token": tok}
    loc = ig_location_id(tok, ig)
    if loc:
        data["location_id"] = loc  # 投稿に「Crea athlete & beauty care」の場所タグを付ける
    r = requests.post(f"{base}/{ig}/media", timeout=T, data=data)
    if not r.ok and loc:
        print("場所タグ付きで失敗したため、場所タグなしで再試行:", r.text[:300])
        data.pop("location_id")
        r = requests.post(f"{base}/{ig}/media", timeout=T, data=data)
    c = _check(r)
    cid = c["id"]
    for _ in range(12):  # 画像の取り込み完了を待つ
        s = _check(requests.get(f"{base}/{cid}", timeout=T,
                                params={"fields": "status_code", "access_token": tok}))
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram画像の取り込みに失敗: {s}")
        time.sleep(5)
    p = _check(requests.post(f"{base}/{ig}/media_publish", timeout=T,
                             data={"creation_id": cid, "access_token": tok}))
    return {"media_id": p["id"]}


# ---------------- Threads ----------------
def post_threads(item):
    if DRY_RUN:
        return {"dry_run": True}
    tok = _env("THREADS_ACCESS_TOKEN")
    uid = os.environ.get("THREADS_USER_ID") or "me"  # IDが未登録でも「me」で本人として投稿できる
    base = "https://graph.threads.net/v1.0"
    c = _check(requests.post(f"{base}/{uid}/threads", timeout=T,
                             data={"media_type": "TEXT", "text": item["text"], "access_token": tok}))
    time.sleep(30)  # Metaの推奨：公開前に約30秒待つ
    p = _check(requests.post(f"{base}/{uid}/threads_publish", timeout=T,
                             data={"creation_id": c["id"], "access_token": tok}))
    return {"media_id": p["id"]}


# ---------------- Googleビジネスプロフィール ----------------
def _google_token():
    r = _check(requests.post("https://oauth2.googleapis.com/token", timeout=T, data={
        "client_id": _env("GBP_CLIENT_ID"), "client_secret": _env("GBP_CLIENT_SECRET"),
        "refresh_token": _env("GBP_REFRESH_TOKEN"), "grant_type": "refresh_token"}))
    return r["access_token"]


def post_gbp(item, booking_url):
    body = {"languageCode": "ja", "summary": item["text"][:1500], "topicType": "STANDARD",
            "callToAction": {"actionType": "BOOK", "url": booking_url}}
    if item.get("image"):
        body["media"] = [{"mediaFormat": "PHOTO", "sourceUrl": image_public_url(item["image"])}]
    if DRY_RUN:
        return {"dry_run": True}
    parent = f"accounts/{_env('GBP_ACCOUNT_ID')}/locations/{_env('GBP_LOCATION_ID')}"
    r = _check(requests.post(f"https://mybusiness.googleapis.com/v4/{parent}/localPosts", timeout=T,
                             json=body, headers={"Authorization": f"Bearer {_google_token()}"}))
    return {"post_name": r.get("name")}


# ---------------- LINE一斉配信（残り通数を確認してから） ----------------
def post_line_broadcast(item):
    if DRY_RUN:
        return {"dry_run": True}
    tok = _env("LINE_CHANNEL_ACCESS_TOKEN")
    h = {"Authorization": f"Bearer {tok}"}
    quota = _check(requests.get("https://api.line.me/v2/bot/message/quota", headers=h, timeout=T))
    used = _check(requests.get("https://api.line.me/v2/bot/message/quota/consumption", headers=h, timeout=T))
    day = (now() - dt.timedelta(days=2)).strftime("%Y%m%d")
    fol = _check(requests.get("https://api.line.me/v2/bot/insight/followers", headers=h, timeout=T,
                              params={"date": day}))
    need = fol.get("targetedReaches") or fol.get("followers") or 0
    left = (quota.get("value") or 0) - (used.get("totalUsage") or 0)
    if quota.get("type") == "limited" and need and left < need:
        raise RuntimeError(f"LINEの残り通数が足りないため配信を見送りました（残り{left}通／必要{need}通）")
    _check(requests.post("https://api.line.me/v2/bot/message/broadcast", headers=h, timeout=T,
                         json={"messages": [{"type": "text", "text": item["text"]}]}))
    return {"sent_to_approx": need, "quota_left_before": left}


# ---------------- ホットペッパー（APIなし → 完成原稿をメールで届ける） ----------------
def post_hpb_blog(item, hpb_admin="https://salonboard.com/login/"):
    notify(f"HPBブログ原稿：{item.get('title','')}",
           "SALON BOARD → 掲載管理 → ブログ に貼り付けて投稿してください（約1分）。\n"
           f"{hpb_admin}\n\n■タイトル\n{item.get('title','')}\n\n■本文\n{item['text']}\n")
    return {"emailed": True}
