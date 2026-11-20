"""Instagramのコメント自動DM
投稿に「相談」などのキーワードをコメントしてくれた方へ、LINEのご相談窓口をDMで送る。
- 30分ごとの予約投稿の実行（crea.publish）の最後に呼ばれる
- 1つのコメントに送るのは1回だけ（data/autodm.json に記録）
- Instagramの決まりで、コメントへのDM返信はコメントから7日以内・1回まで
"""
import datetime as dt, json, os, requests
from .common import config, now, notify
from . import compliance
from .publishers import IG_HOST, IG_VER, T, _env, ig_user_id

STATE = os.path.join(os.path.dirname(__file__), "..", "data", "autodm.json")


def _load():
    try:
        return json.load(open(STATE))
    except Exception:
        return {"replied": {}}


def _save(s):
    json.dump(s, open(STATE, "w"), ensure_ascii=False, indent=2)


def dm_text(cfg):
    c = cfg["clinic"]
    return (
        "コメントありがとうございます。Creaです😊\n\n"
        "ここまで、ひとりで様子を見ながら頑張ってこられたのだと思います。\n"
        "「こんなことで相談していいのかな」と迷う内容でも大丈夫です。\n\n"
        "ご相談・ご予約はこちらのLINEからどうぞ。気になっていることを、そのまま送ってください。\n"
        f"{c['line_url']}\n\n"
        f"Crea athlete & beauty care（JR三島駅南口 徒歩3分／完全予約制・1対1）\n"
        f"ネット予約：{c['hotpepper']}"
    )


def run():
    cfg = config()
    a = cfg.get("autodm") or {}
    if not a.get("enabled", True):
        return []
    try:
        tok = _env("IG_ACCESS_TOKEN")
    except Exception:
        return []
    iid = ig_user_id(tok)
    base = f"https://{IG_HOST}/{IG_VER}"
    words = a.get("keywords", ["相談"])
    me = (a.get("own_username") or "crea_mishima").lower()
    text = dm_text(cfg)
    if compliance.check(text, "instagram"):
        return ["自動DMの文面にNG表現があるため停止しました"]

    st = _load()
    done = st.setdefault("replied", {})
    errors, sent = [], 0
    since = now() - dt.timedelta(days=7)
    media = requests.get(f"{base}/{iid}/media", timeout=T, params={
        "fields": "id,timestamp,comments_count", "limit": 15, "access_token": tok}).json().get("data", [])
    for m in media:
        if not m.get("comments_count"):
            continue
        cs = requests.get(f"{base}/{m['id']}/comments", timeout=T, params={
            "fields": "id,text,username,timestamp", "limit": 50, "access_token": tok}).json().get("data", [])
        for c in cs:
            cid = c["id"]
            if cid in done or (c.get("username") or "").lower() == me:
                continue
            ts = dt.datetime.fromisoformat(c["timestamp"].replace("+0000", "+00:00"))
            if ts < since:
                continue
            if not any(w in (c.get("text") or "") for w in words):
                continue
            ok, err = False, ""
            for url in (f"{base}/{iid}/messages", f"{base}/me/messages"):
                r = requests.post(url, timeout=T, params={"access_token": tok}, json={
                    "recipient": {"comment_id": cid}, "message": {"text": text}})
                if r.ok:
                    ok = True
                    break
                err = r.text[:300]
            rec = {"at": now().isoformat(), "user": c.get("username"), "media": m["id"], "dm": ok}
            if ok:
                sent += 1
                # コメント欄にも一言返す（失敗しても気にしない）
                requests.post(f"{base}/{cid}/replies", timeout=T, params={
                    "message": a.get("public_reply", "コメントありがとうございます！DMをお送りしましたのでご確認ください😊"),
                    "access_token": tok})
            else:
                rec["error"] = err
                errors.append(f"@{c.get('username')} へのDMに失敗: {err}")
            done[cid] = rec
    _save(st)
    if sent:
        print(f"自動DM: {sent}件送信")
    if errors:
        notify("Instagramの自動DMが送れませんでした",
               "\n".join(errors) + "\n\nInstagramアプリの「メッセージへのアクセスを許可」がオンになっているか確認してください。")
    return errors


if __name__ == "__main__":
    run()
