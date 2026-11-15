"""毎晩の数字集計（22時ごろ）

1. Instagram・Threadsの数字を集めて data/performance.json を更新（次の週の企画が読む）
2. 投稿の一覧を data/log/posts.csv に書き出す（表計算ソフトやGoogleスプレッドシートで開ける）
3. その日のまとめを data/log/daily.csv に1行足す
4. メールで知らせる：今日出した投稿／保留・失敗／伸びた投稿／冒頭フックの型ごとの成績／
   今月のClaude API使用量／明日の予定

実行: python -m crea.report
"""
import csv
import datetime as dt
import io

from .common import DATA, LOG, DRY_RUN, all_queue_items, config, load_json, notify, now, save_json
from . import insights
from .generate import hook_stats

CH_NAME = {"instagram": "Instagram", "threads": "Threads", "gbp": "Googleマップ", "hpb_blog": "HPBブログ",
           "ameblo": "アメブロ", "line_broadcast": "LINE"}
METRIC_COLS = ["reach", "views", "likes", "comments", "replies", "saved", "shares", "reposts"]


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    path.write_text("﻿" + buf.getvalue(), encoding="utf-8")  # BOM付き＝Excelで文字化けしない


def month_usage(costs, month):
    runs = [r for r in costs.get("runs", []) if r.get("date", "").startswith(month)]
    tot = {k: sum(r.get(k, 0) for r in runs) for k in ("input_tokens", "output_tokens", "web_searches")}
    return len(runs), tot


def yen_estimate(tot, cfg):
    """config.yaml の ai.pricing が入っている時だけ、円の目安を出す（入っていなければ None）"""
    pr = (cfg.get("ai") or {}).get("pricing") or {}
    try:
        usd = (tot["input_tokens"] / 1e6 * float(pr["input_per_mtok_usd"])
               + tot["output_tokens"] / 1e6 * float(pr["output_per_mtok_usd"])
               + tot["web_searches"] / 1000 * float(pr.get("search_per_1000_usd", 0)))
        return round(usd * float(pr["usd_jpy"]))
    except (KeyError, TypeError, ValueError):
        return None


def main():
    cfg = config()
    t = now()
    today, tomorrow = t.date().isoformat(), (t.date() + dt.timedelta(days=1)).isoformat()

    # 1) 数字を集める（鍵がない・テストの時は前回の記録をそのまま使う）
    perf_path = DATA / "performance.json"
    posts = [] if DRY_RUN else insights.collect()
    if posts:
        save_json(perf_path, {"posts": posts, "updated_at": t.isoformat()})
    else:
        posts = load_json(perf_path, {"posts": []})["posts"]
    by_id = {p["id"] + p.get("posted_at", "")[:10]: p for p in posts}

    # 2) 投稿の一覧（全媒体。数字が取れる媒体は数字つき）
    rows, today_posts, trouble, next_up = [], [], [], []
    for _, q in all_queue_items():
        for it in q["items"]:
            st = it.get("status")
            sched = it.get("scheduled_at", "")
            if st in ("held", "failed", "duplicate") and sched[:10] >= (t.date() - dt.timedelta(days=2)).isoformat():
                why = ([x["word"] for x in it.get("compliance", [])]
                       + [x["msg"] for x in it.get("lint", []) if x["level"] == "error"]
                       + ([it["last_error"][:80]] if it.get("last_error") else []))
                trouble.append(f"・[{st}] {it['id']} {why}")
            if st == "pending" and sched[:10] == tomorrow:
                next_up.append(f"・{sched[11:16]} {CH_NAME.get(it['channel'], it['channel'])} — {it.get('topic', '')}")
            if st not in ("posted", "manual"):
                continue
            posted_at = (it.get("posted_at") or "")[:16]
            p = by_id.get(it["id"] + posted_at[:10], {})
            m = p.get("metrics", {})
            first = next((l.strip() for l in it.get("text", "").split("\n") if l.strip()), "")
            rows.append([posted_at.replace("T", " "), CH_NAME.get(it["channel"], it["channel"]), it["id"],
                         it.get("hook", ""), it.get("topic", ""), first[:60]]
                        + [m.get(c, "") for c in METRIC_COLS] + [p.get("score", "")])
            if posted_at[:10] == today:
                today_posts.append(f"・{posted_at[11:16]} {CH_NAME.get(it['channel'], it['channel'])} — {it.get('topic', '')}")
    rows.sort(key=lambda r: r[0])
    write_csv(LOG / "posts.csv", ["投稿日時", "媒体", "id", "フックの型", "テーマ", "1行目"]
              + ["リーチ", "表示", "いいね", "コメント", "返信", "保存", "シェア", "リポスト", "スコア"], rows)

    # 3) その日のまとめを1行
    recent = [p for p in posts if p.get("posted_at", "")[:10] >= (t.date() - dt.timedelta(days=7)).isoformat()]
    views = sum((p["metrics"].get("views") or 0) + (p["metrics"].get("reach") or 0) for p in recent)
    likes = sum(p["metrics"].get("likes") or 0 for p in recent)
    saves = sum((p["metrics"].get("saved") or 0) + (p["metrics"].get("shares") or 0)
                + (p["metrics"].get("reposts") or 0) for p in recent)
    n_runs, tot = month_usage(load_json(DATA / "costs.json", {"runs": []}), today[:7])
    daily_path = LOG / "daily.csv"
    header = ["日付", "今日の投稿数", "直近7日の表示・リーチ", "直近7日のいいね", "直近7日の保存・シェア",
              "今月の入力トークン", "今月の出力トークン", "今月の検索回数"]
    old = []
    if daily_path.exists():
        old = [r for r in csv.reader(io.StringIO(daily_path.read_text(encoding="utf-8").lstrip("﻿")))][1:]
    old = [r for r in old if r and r[0] != today][-400:]
    write_csv(daily_path, header, old + [[today, len(today_posts), views, likes, saves,
                                          tot["input_tokens"], tot["output_tokens"], tot["web_searches"]]])

    # 4) メール
    lines = [f"{t:%m月%d日}のまとめ", "", f"▼今日出した投稿（{len(today_posts)}件）"] + (today_posts or ["・なし"])
    if trouble:
        lines += ["", "▼止まっている投稿（対応が必要）"] + trouble
    scored = sorted([p for p in recent if p.get("score") is not None], key=lambda p: p["score"], reverse=True)
    if scored:
        lines += ["", "▼直近7日で伸びた投稿"] + [
            f"・[{CH_NAME.get(p['channel'], p['channel'])}] {p.get('hook', '')} {p.get('first_line', '')} … {p['metrics']}"
            for p in scored[:3]]
        lines += ["", f"直近7日の合計：表示・リーチ {views:,}／いいね {likes:,}／保存・シェア {saves:,}"]
    st = hook_stats(posts)
    if st:
        lines += ["", "▼冒頭フックの型ごとの平均スコア（knowledge/hooks.md の番号）"] + [
            f"・[{CH_NAME.get(ch, ch)}] {hk}: 平均{avg}（{n}件）"
            for (ch, hk), (n, avg) in sorted(st.items(), key=lambda kv: (kv[0][0], -kv[1][1]))]
    yen = yen_estimate(tot, cfg)
    lines += ["", f"▼今月のClaude API使用量（生成{n_runs}回）",
              f"・入力 {tot['input_tokens']:,}／出力 {tot['output_tokens']:,} トークン、検索 {tot['web_searches']}回"
              + (f"（目安 約{yen:,}円）" if yen is not None else "")]
    lines += ["", f"▼明日の予定（{len(next_up)}件）"] + (sorted(next_up) or ["・なし"])
    lines += ["", "投稿の一覧: data/log/posts.csv ／ 日ごとの推移: data/log/daily.csv"]
    body = "\n".join(lines)
    rep = cfg.get("report") or {}
    quiet = not rep.get("daily_email", True) or (rep.get("only_when_needed") and not (today_posts or trouble))
    if quiet:
        print(body)
    else:
        notify(f"今日のまとめ（投稿{len(today_posts)}件" + ("・要対応あり" if trouble else "") + "）", body)


if __name__ == "__main__":
    main()
