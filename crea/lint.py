"""点検スクリプト（構成の抜け・決めごと・重複）

compliance.py が「使ってはいけない言葉」を見るのに対し、こちらは
「入っているべきものが入っているか」「オーナーの決めごとを守っているか」
「前に出した投稿と同じになっていないか」を見ます。

  level = "error"   … 保留にする（そのまま出すと困るもの）
  level = "warn"    … 予約はするが、週次メールと点検結果に出す（直すと良くなるもの）

実行: python -m crea.lint              （いちばん新しい予約ファイルの pending を点検）
      python -m crea.lint data/queue/week-2026-11-16.json
"""
import datetime as dt
import difflib
import re
import sys
from pathlib import Path

from .common import QUEUE, all_queue_items, clean_text, config, load_json

PHONE = re.compile(r"\d{2,4}-\d{2,4}-\d{3,4}")
BENEFIT = re.compile(r"ドリンクサービス|カウンセリング(を)?長め|LINE限定")
PRICE = re.compile(r"\d[\d,]*\s?円|半額|割引|無料体験|[0-9０-９]+\s?[%％]\s?(OFF|オフ|引き)", re.I)
HOURS = re.compile(r"(\d{1,2}[:：]\d{2})\s?[〜~～\-－]\s?(\d{1,2}[:：]\d{2})")
HASHTAG = re.compile(r"[#＃][^\s#＃]+")
REVIEW_TRADE = re.compile(r"口コミ[^。\n]*(特典|プレゼント|割引|サービス|クーポン)|(特典|プレゼント|割引|クーポン)[^。\n]*口コミ")
LINE_URL = re.compile(r"lin\.ee/\w+")

TITLE_MAX = {"hpb_blog": 30, "ameblo": 32}
HASHTAG_MAX = {"instagram": 5, "threads": 1}
NEED_BOTH_URLS = ("instagram", "gbp", "ameblo")
DUP_SAME_CHANNEL = 0.85   # 同じ媒体でこれ以上似ていたら「同じ投稿」とみなす
DUP_DAYS = 60


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", clean_text(text or ""))


def _w(level, code, msg):
    return {"level": level, "code": code, "msg": msg}


def lint(item: dict, cfg: dict, history: list[dict] | None = None) -> list[dict]:
    """1件の投稿を点検して、気になる点の一覧を返す。空なら合格。"""
    ch = item.get("channel", "")
    text = item.get("text") or ""
    title = item.get("title") or ""
    clinic = cfg.get("clinic", {})
    out = []

    # --- オーナーの決めごと（knowledge/feedback.md） ---
    if PHONE.search(text):
        out.append(_w("warn", "電話番号", "電話番号が入っています（載せない決まり。公開時に自動で取り除きます）"))
    if BENEFIT.search(text):
        out.append(_w("warn", "LINE特典", "LINE特典（カウンセリング長め・ドリンク）に触れています（書かない決まり）"))
    if PRICE.search(title + "\n" + text):
        out.append(_w("warn", "料金", f"料金・割引の表現があります：「{PRICE.search(title + chr(10) + text).group(0)}」"))
    if REVIEW_TRADE.search(text):
        out.append(_w("error", "口コミ特典", "口コミのお願いが特典・割引と同じ文にあります（引き換えは不可）"))

    # --- 予約の出口 ---
    hpb = (clinic.get("hotpepper") or "").rstrip("/")
    has_hpb = bool(hpb) and hpb in text
    has_line = bool(LINE_URL.search(text))
    if ch in NEED_BOTH_URLS and not (has_hpb and has_line):
        miss = "・".join(n for n, ok in (("ホットペッパー", has_hpb), ("LINE", has_line)) if not ok)
        out.append(_w("warn", "予約URL", f"予約先のURLがありません：{miss}（両方載せる決まり）"))
    if ch == "hpb_blog" and not has_hpb:
        out.append(_w("warn", "予約URL", "ホットペッパーの予約URLがありません"))

    # --- 事実（config.yaml と合っているか） ---
    m = HOURS.search(text)
    if m:
        got = f"{m.group(1)}〜{m.group(2)}".replace("：", ":")
        if got not in (clinic.get("hours") or "").replace("：", ":"):
            out.append(_w("warn", "営業時間", f"営業時間が config.yaml と違います：{got}"))

    # --- 媒体ごとの形 ---
    n = len(text)
    if ch == "threads" and n > 400:
        out.append(_w("warn", "長さ", f"Threadsが{n}字です（400字以内）"))
    tags = HASHTAG.findall(text)
    if ch in HASHTAG_MAX and len(tags) > HASHTAG_MAX[ch]:
        out.append(_w("warn", "ハッシュタグ", f"ハッシュタグが{len(tags)}個です（{HASHTAG_MAX[ch]}個まで）"))
    if ch == "instagram" and tags and not any("三島" in t for t in tags):
        out.append(_w("warn", "ハッシュタグ", "地域名（#三島 など）のハッシュタグがありません"))
    if ch in TITLE_MAX:
        if not title.strip():
            out.append(_w("error", "タイトル", "タイトルがありません"))
        elif len(title) > TITLE_MAX[ch]:
            out.append(_w("warn", "タイトル", f"タイトルが{len(title)}字です（{TITLE_MAX[ch]}字以内）"))
        if title and not any(k in title for k in ("三島", "長泉", "沼津", "清水町", "裾野")):
            out.append(_w("warn", "タイトル", "タイトルに地域名（三島 など）がありません"))
    if ch == "gbp":
        head = "\n".join([l for l in text.splitlines() if l.strip()][:2])
        if "三島" not in head:
            out.append(_w("warn", "冒頭", "冒頭2行に「三島」がありません（Googleマップは地域名を先頭に）"))
    if ch in ("instagram", "gbp"):
        hl = (item.get("headline") or "").replace("\\n", "").replace("\n", "")
        if not hl:
            out.append(_w("warn", "画像見出し", "画像の見出し（headline）がありません"))
        elif len(hl) > 20:
            out.append(_w("warn", "画像見出し", f"画像の見出しが{len(hl)}字です（20字以内）"))
    if not _first_line(text):
        out.append(_w("error", "本文", "本文が空です"))

    # --- 同じ投稿を2回出さない ---
    me = _norm(text)
    my_first = _first_line(text)
    seen = set()

    def add(level, code, msg):
        if code not in seen:
            seen.add(code)
            out.append(_w(level, code, msg))

    for h in history or []:
        if h is item or (h.get("id") == item.get("id") and h.get("scheduled_at") == item.get("scheduled_at")):
            continue
        other = _norm(h.get("text"))
        if not other:
            continue
        same_ch = h.get("channel") == ch
        pair = {ch, h.get("channel")} == {"hpb_blog", "ameblo"}
        if not (same_ch or pair):
            continue
        ref = f"{h.get('id')}（{h.get('scheduled_at', '')[:10]}）"
        sm = difflib.SequenceMatcher(None, me, other, autojunk=False)
        ratio = 1.0 if me == other else (sm.ratio() if sm.quick_ratio() >= DUP_SAME_CHANNEL else 0.0)
        if same_ch and ratio >= DUP_SAME_CHANNEL:
            add("error", "重複", f"{ref} とほぼ同じ文です")
        elif same_ch and my_first and my_first == _first_line(h.get("text") or ""):
            add("warn", "1行目", f"1行目が {ref} と同じです（毎回変える）")
        elif pair and ratio >= 0.95:
            add("warn", "書き分け", f"{ref} と同じ文です（アメブロはアメブロ用に書き分ける）")
    return out


def history_items(days: int = DUP_DAYS, now: dt.datetime | None = None) -> list[dict]:
    """重複チェックの相手にする、最近の投稿（見送り・期限切れは除く）"""
    now = now or dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    cutoff = now - dt.timedelta(days=days)
    out = []
    for _, q in all_queue_items():
        for it in q.get("items", []):
            if it.get("status") in ("skip", "expired", "duplicate"):
                continue
            try:
                if dt.datetime.fromisoformat(it["scheduled_at"]) < cutoff:
                    continue
            except (KeyError, ValueError):
                continue
            out.append(it)
    return out


def summarize(issues: list[dict]) -> str:
    return " / ".join(f"{'✖' if i['level'] == 'error' else '△'}{i['code']}" for i in issues)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    files = sorted(QUEUE.glob("week-*.json"))
    path = Path(argv[0]) if argv else (files[-1] if files else None)
    if not path or not path.exists():
        print("予約ファイルがありません"); return 0
    cfg = config()
    hist = history_items()
    q = load_json(path, {"items": []})
    errors = warns = 0
    print(f"点検: {path.name}")
    for it in q["items"]:
        if it.get("status") not in ("pending", "held"):
            continue
        issues = lint(it, cfg, hist)
        errors += sum(i["level"] == "error" for i in issues)
        warns += sum(i["level"] == "warn" for i in issues)
        mark = "✖" if any(i["level"] == "error" for i in issues) else ("△" if issues else "○")
        print(f"{mark} {it['id']}  {it.get('topic', '')}")
        for i in issues:
            print(f"    {'✖' if i['level'] == 'error' else '△'} [{i['code']}] {i['msg']}")
    print(f"\n結果: ✖{errors}件 / △{warns}件")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
