"""投稿の反応を集めて data/performance.json に記録 → 次週の生成で「伸びた型」を増やす
（毎週の生成の直前に実行）"""
import os, requests
from .common import DATA, DRY_RUN, all_queue_items, save_json, notify

IG_VER = os.environ.get("IG_API_VERSION", "v23.0")
IG_HOST = os.environ.get("IG_API_HOST") or "graph.facebook.com"


def _get(url, params):
    try:
        r = requests.get(url, params=params, timeout=30)
        return r.json() if r.ok else {}
    except Exception:
        return {}


def ig_metrics(mid, tok):
    d = _get(f"https://{IG_HOST}/{IG_VER}/{mid}",
             {"fields": "like_count,comments_count", "access_token": tok})
    ins = _get(f"https://{IG_HOST}/{IG_VER}/{mid}/insights",
               {"metric": "reach,saved,shares", "access_token": tok})
    m = {"likes": d.get("like_count", 0), "comments": d.get("comments_count", 0)}
    for x in ins.get("data", []):
        m[x["name"]] = (x.get("values") or [{}])[0].get("value", 0)
    # 保存・シェアを重く評価（アルゴリズムで重視される）
    m_score = m.get("reach", 0) * 0.01 + m["likes"] + m["comments"] * 3 + m.get("saved", 0) * 5 + m.get("shares", 0) * 5
    return m, round(m_score, 1)


def threads_metrics(mid, tok):
    ins = _get(f"https://graph.threads.net/v1.0/{mid}/insights",
               {"metric": "views,likes,replies,reposts", "access_token": tok})
    m = {x["name"]: (x.get("values") or [{}])[0].get("value", 0) for x in ins.get("data", [])}
    score = m.get("views", 0) * 0.01 + m.get("likes", 0) + m.get("replies", 0) * 3 + m.get("reposts", 0) * 4
    return m, round(score, 1)


def main():
    if DRY_RUN:
        print("DRY_RUN: 実績取得はスキップ"); return
    ig_tok, th_tok = os.environ.get("IG_ACCESS_TOKEN"), os.environ.get("THREADS_ACCESS_TOKEN")
    posts = []
    for _, q in all_queue_items():
        for it in q["items"]:
            mid = (it.get("result") or {}).get("media_id")
            if it.get("status") != "posted" or not mid:
                continue
            if it["channel"] == "instagram" and ig_tok:
                m, s = ig_metrics(mid, ig_tok)
            elif it["channel"] == "threads" and th_tok:
                m, s = threads_metrics(mid, th_tok)
            else:
                continue
            posts.append({"id": it["id"], "channel": it["channel"], "topic": it.get("topic"),
                          "first_line": it["text"].split("\n")[0][:60], "metrics": m, "score": s})
    save_json(DATA / "performance.json", {"posts": posts[-200:]})
    if posts:
        top = sorted(posts, key=lambda p: p["score"], reverse=True)[:3]
        notify("先週までの反応レポート", "伸びた投稿 TOP3\n" + "\n".join(
            f"・[{p['channel']}] {p['topic']} … {p['metrics']}" for p in top))


if __name__ == "__main__":
    main()
