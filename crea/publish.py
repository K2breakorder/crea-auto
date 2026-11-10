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


def main():
    cfg = config()
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
            full = (it.get("title", "") + "\n" + it["text"]) if it["channel"] == "hpb_blog" else it["text"]
            ng = compliance.check(full, it["channel"])
            if ng and cfg["safety"]["hold_on_any_ng"]:
                it["status"] = "held"; it["compliance"] = ng; changed = True
                failures.append(f"{it['id']}: NG表現のため保留 {[x['word'] for x in ng]}")
                continue
            try:
                ch = it["channel"]
                if ch == "instagram":
                    res = P.post_instagram(it)
                elif ch == "threads":
                    res = P.post_threads(it)
                elif ch == "gbp":
                    res = P.post_gbp(it, cfg["clinic"]["line_url"])  # 予約ボタンはLINEへ
                elif ch == "line_broadcast":
                    res = P.post_line_broadcast(it)
                elif ch == "hpb_blog":
                    res = P.post_hpb_blog(it)
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
    if failures:
        notify("投稿できなかったものがあります",
               "\n".join(failures) + "\n\n多くはトークン期限切れ・設定漏れです。手順書の『困ったとき』を見てください。")


if __name__ == "__main__":
    main()
