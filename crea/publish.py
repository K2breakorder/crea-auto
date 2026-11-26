"""予約時刻を過ぎた投稿を各媒体に出す（GitHub Actionsで30分ごとに実行）

実行: python -m crea.publish
"""
import datetime as dt, traceback, re
from .common import config, now, all_queue_items, save_json, notify
from . import compliance, publishers as P

GRACE_HOURS = 12  # 予約時刻から12時間以上遅れたものは出さない（古い話題を防ぐ）


def clean_text(t):
    """店舗情報から電話番号の行と、LINEの後ろの特典カッコ書きを取り除く"""
    t = re.sub(r"^.*(TEL|電話|☎)[^\n]*\d{2,4}-\d{2,4}-\d{3,4}.*\n?", "", t, flags=re.M)
    t = re.sub(r"\d{2,4}-\d{3,4}-\d{4}", "", t)
    t = re.sub(r"(LINE)\s*[（(][^）)\n]*(カウンセリング|ドリンク|特典)[^）)\n]*[）)]", r"\1", t)
    t = re.sub(r"(LINE)\s*[：:][^\n]*ドリンクサービス[^\n]*", r"\1", t)
    # 特典の文（カウンセリング長め・ドリンクサービス）を文ごと取り除く
    t = re.sub(r"^[^\n。]*ドリンクサービス[^\n。]*$\n?", "", t, flags=re.M)
    t = re.sub(r"[^。\n]*ドリンクサービス[^。\n]*。", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


def ig_to_gbp_text(it, cfg):
    """Instagramの投稿文をGoogleマップ用に整える（同じ内容・同時刻で出すため）"""
    lines = []
    for ln in it["text"].splitlines():
        if re.match(r"^\s*(#\S+\s*)+$", ln):        # ハッシュタグだけの行
            continue
        if "保存" in ln and ln.strip().startswith(("▶", "▷", "→", "📌", "＼")):  # 「保存してね」の呼びかけ
            continue
        lines.append(ln)
    t = "\n".join(lines).strip()
    head = it.get("headline", "").replace("\n", "")
    if head and head not in t[:80]:
        t = f"【三島駅南口徒歩3分】{head}\n\n" + t
    c = cfg["clinic"]
    if c["hotpepper"] not in t:
        t += f"\n▶ネット予約（ホットペッパービューティー）\n{c['hotpepper']}"
    if c["line_url"] not in t:
        t += f"\n▶LINE（下の「予約」ボタンからも）\n{c['line_url']}"
    return clean_text(t)[:1500]


def mirror_to_gbp(it, cfg):
    """Instagramと同じ内容・同じ時刻でGoogleマップにも投稿する（失敗してもInstagramには影響させない）"""
    if not cfg["channels"]["instagram"].get("mirror_to_gbp", True) or it.get("gbp_mirror"):
        return None
    g = {"text": ig_to_gbp_text(it, cfg), "image": it.get("image")}
    ng = compliance.check(g["text"], "gbp")
    if ng:
        it["gbp_mirror"] = {"status": "held", "ng": [x["word"] for x in ng]}
        return f"Googleマップ転載はNG表現のため保留 {[x['word'] for x in ng]}"
    try:
        res = P.post_gbp(g, cfg["clinic"]["line_url"])
        it["gbp_mirror"] = {"status": "posted", "posted_at": now().isoformat(), "result": res}
    except P.MissingConfig:
        it["gbp_mirror"] = {"status": "skipped"}
    except Exception as e:
        it["gbp_mirror"] = {"status": "failed", "error": str(e)[:300]}
        return f"Googleマップ転載に失敗: {e}"
    return None


def main():
    cfg = config()
    # Threadsの追加投稿（1日10本）を2日先まで用意する（失敗しても投稿処理は続ける）
    try:
        from . import threads_extra
        threads_extra.fill(cfg)
    except Exception as e:
        print("Threads追加投稿の作成でエラー:", e)
    t = now()
    done_today = 0
    for _, q in all_queue_items():
        done_today += sum(1 for it in q["items"]
                          if it.get("posted_at", "")[:10] == t.date().isoformat())
    failures, posted = [], []

    for path, q in all_queue_items():
        changed = False
        for it in q["items"]:
            if it.get("status") != "pending":
                continue
            when = dt.datetime.fromisoformat(it["scheduled_at"])
            if when > t:
                continue
            if t - when > dt.timedelta(hours=GRACE_HOURS):
                it["status"] = "expired"; changed = True; continue
            if done_today >= cfg["safety"]["max_posts_per_day"]:
                break
            it["text"] = clean_text(it["text"])
            # 投稿直前にもう一度NGチェック（手で直した場合も安全に）
            full = (it.get("title", "") + "\n" + it["text"]) if it["channel"] in ("hpb_blog", "ameblo") else it["text"]
            ng = compliance.check(full, it["channel"])
            if ng and cfg["safety"]["hold_on_any_ng"]:
                it["status"] = "held"; it["compliance"] = ng; changed = True
                failures.append(f"{it['id']}: NG表現のため保留 {[x['word'] for x in ng]}")
                continue
            try:
                ch = it["channel"]
                if ch == "instagram":
                    res = P.post_instagram(it)
                    it.update(status="posted", posted_at=now().isoformat(), result=res)
                    err = mirror_to_gbp(it, cfg)   # 同じ内容・同時刻でGoogleマップにも
                    if err:
                        failures.append(f"{it['id']}: {err}")
                elif ch == "threads":
                    res = P.post_threads(it)
                elif ch == "gbp":
                    res = P.post_gbp(it, cfg["clinic"]["line_url"])  # 予約ボタンはLINEへ
                elif ch == "line_broadcast":
                    res = P.post_line_broadcast(it)
                elif ch == "hpb_blog":
                    res = P.post_hpb_blog(it)
                elif ch == "ameblo":
                    res = P.post_ameblo(it)
                else:
                    continue
                it.update(status="posted", posted_at=now().isoformat(), result=res)
                posted.append(f"{ch}: {it.get('topic','')}")
                done_today += 1
            except P.MissingConfig as e:
                # まだ連携していない媒体 → 原稿をメールで届けて手動投稿してもらう
                notify(f"{it['channel']}は未連携のため原稿をお送りします",
                       f"({e})\n予定: {it['scheduled_at'][:16]}\n\n{it.get('title','')}\n{it['text']}")
                it.update(status="manual", posted_at=now().isoformat())
            except Exception as e:
                it["attempts"] = it.get("attempts", 0) + 1
                it["last_error"] = str(e)[:500]
                if it["attempts"] >= 3:
                    it["status"] = "failed"
                    failures.append(f"{it['id']}: {e}")
                traceback.print_exc()
            changed = True
        if changed:
            save_json(path, q)

    print("投稿:", posted or "なし")
    # Instagramのコメント「相談」へ自動DM（失敗しても投稿処理には影響させない）
    try:
        from . import autodm
        autodm.run()
    except Exception as e:
        print("自動DMでエラー:", e)
    if failures:
        notify("投稿できなかったものがあります",
               "\n".join(failures) + "\n\n多くはトークン期限切れ・設定漏れです。手順書の『困ったとき』を見てください。")


if __name__ == "__main__":
    main()
