"""毎週の投稿を自動で作る（最新情報を調べる → 文章 → 法規チェック → 画像 → 予約キューへ）

実行: python -m crea.generate
"""
import json, os, re, datetime as dt
from . import compliance
from .common import (DATA, QUEUE, DRY_RUN, config, now, load_json, save_json,
                     all_queue_items, notify)
from .images import make_card

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

CHANNEL_GUIDE = {
    "instagram": "Instagramフィード投稿。画像用の見出し(headline 20字以内。読みやすい位置に改行\\nを1つ入れる)とサブ(sub 40字以内)、タグ(tag 8字以内)も作る。"
                 "キャプションは1行目で手を止めさせる→共感→からだの仕組みの解説→今日からできるセルフケア1つ→"
                 "『保存して見返してね』など行動のお願い1つ→店舗情報→ハッシュタグ5個以内（#三島 #三島駅 など地域名を含める）。600〜1000字。",
    "threads": "Threads投稿。350字以内（絶対に400字を超えない）。会話調で、1つの気づきだけを伝える。ハッシュタグは0〜1個。"
               "宣伝色は薄く、プロフィールに興味を持たせる。",
    "gbp": "Googleビジネスプロフィール（Googleマップ）の最新情報投稿。300〜600字。冒頭に『三島駅南口徒歩3分』など地域名と"
           "来院のきっかけになる悩みを自然に入れる（MEO対策）。画像用の headline / sub / tag も作る。最後に予約導線。",
    "hpb_blog": "ホットペッパービューティーのブログ。タイトル(title 30字以内)と本文1000〜1500字。"
                "HPBでは『鍼・灸・医学・病院・医療・あん摩・マッサージ指圧』は使えない。鍼灸は『東洋の叡智』と表現する。"
                "最後にクーポン予約への自然な誘導。",
    "line_broadcast": "LINE一斉配信。250字以内。ブロックされないよう、売り込みより『役立つ・ちょっと嬉しい』を優先。"
                      "季節の気づき＋LINE限定特典（カウンセリング長め＋ドリンクサービス）＋予約導線（HPBかLINEで返信）。",
}


def week_slots(cfg, start: dt.date):
    """start(月曜)から7日間の投稿枠を作る"""
    slots = []
    for ch, c in cfg["channels"].items():
        if not c.get("enabled"):
            continue
        if ch == "line_broadcast":
            s = c["slot"]
            d = start + dt.timedelta(days=DAYS.index(s["day"]))
            week_no = (d.day - 1) // 7 + 1
            if week_no in c.get("weeks_of_month", [1]):
                slots.append((ch, d, s["time"]))
            continue
        for s in c["slots"]:
            slots.append((ch, start + dt.timedelta(days=DAYS.index(s["day"])), s["time"]))
    return sorted(slots, key=lambda x: (x[1], x[2].zfill(5)))


def recent_topics(days=45):
    cutoff = now() - dt.timedelta(days=days)
    out = []
    for _, q in all_queue_items():
        for it in q["items"]:
            if dt.datetime.fromisoformat(it["scheduled_at"]) >= cutoff:
                out.append(f'{it["channel"]}: {it.get("topic", "")}')
    return out[-60:]


def performance_summary():
    perf = load_json(DATA / "performance.json", {"posts": []})
    posts = [p for p in perf["posts"] if p.get("score") is not None]
    if not posts:
        return "（まだ実績データなし）"
    posts.sort(key=lambda p: p["score"], reverse=True)
    top = "\n".join(f'- 好調: [{p["channel"]}] {p.get("topic","")}（{p.get("metrics")}）' for p in posts[:5])
    low = "\n".join(f'- 不調: [{p["channel"]}] {p.get("topic","")}（{p.get("metrics")}）' for p in posts[-3:])
    return top + "\n" + low


def clinic_block(cfg):
    c = cfg["clinic"]
    return f"""## 店舗情報（ここにない事実は書かない）
- 店名: {c['name']}（静岡県三島市）
- コンセプト: {c['concept']}
- ターゲット: {c['target']}
- 住所: {c['address']}（{c['access']}）／駐車場: {c['parking']}
- 営業: {c['hours']}／電話: {c['phone']}／支払い: {c['payment']}
- 施術者: {c['qualifications']}
- メニュー: {' / '.join(c['menus'])}
- LINE: {c['line_url']}（{c['line_benefit']}）
- 予約: ホットペッパービューティー {c['hotpepper']} ／ 公式サイト {c['website']}"""


def rules_block():
    return f"""## 法規ルール（あはき・柔整広告ガイドライン、薬機法、景品表示法）— 厳守
- 効果を断定しない（「〜が楽になる方が多い」「〜を目指す」「〜をサポート」など）
- 最上級・他院比較・保証・体験談・ビフォーアフター・病名・「治療/患者/診療」の語は使わない
- 料金や割引は書かない（クーポンは予約ページで確認、と誘導する）
- 下記の語は全媒体で使用禁止:
{compliance.rules_as_prompt('instagram')}
- hpb_blog だけは、さらに次の語も使用禁止（鍼灸は「東洋の叡智」と言い換える）:
{compliance.rules_as_prompt('hpb_blog', hpb_only=True)}"""


def research(cfg, start):
    """ステップ1: 最新情報を検索して、来週のテーマと材料をまとめる"""
    prompt = f"""あなたは静岡県三島市の整体・美容ケアサロン「{cfg['clinic']['name']}」の集客担当です。
{start:%Y年%m月%d日}からの1週間の投稿づくりのために、web検索で最新情報を調べてください。
1. 来週の静岡・三島周辺の天気・気温の傾向と、季節の体調トピック
2. 三島周辺の来週の行事・イベント（あれば）
3. 40〜60代女性のからだ・美容で今話題になっていること
4. Instagram・Threads・Googleマップ運用の最近のポイント

ターゲット: {cfg['clinic']['target']}

## 過去の実績（好調な型を増やし、不調な型は変える）
{performance_summary()}

## 最近扱ったテーマ（重複させない）
{chr(10).join(recent_topics()) or '（なし）'}

調べ終えたら、次の形式だけで答える（前置き不要）:
テーマ: （来週の投稿全体の軸を一言）
メモ:
- （投稿に使える事実を箇条書きで6〜10個。それぞれ出典URLを括弧で添える。不確かなものは書かない）
- （好調だった型を踏まえた来週の作り方の方針を1〜2行）"""
    tools = [{"type": cfg["ai"]["web_search_tool"], "name": "web_search",
              "max_uses": cfg["ai"]["max_searches"],
              "user_location": {"type": "approximate", "city": "Mishima", "region": "Shizuoka",
                                "country": "JP", "timezone": "Asia/Tokyo"}}]
    text = call_claude(prompt, cfg["ai"]["model"], tools, max_tokens=6000)
    m = re.search(r"テーマ[:：]\s*(.+)", text)
    theme = m.group(1).strip() if m else "季節のからだケア"
    notes = text[text.find("メモ"):] if "メモ" in text else text[-3000:]
    return theme, notes.strip()


def build_channel_prompt(cfg, ch, slots, theme, notes):
    """ステップ2: 媒体ごとに投稿を書く"""
    slot_lines = "\n".join(
        f'- id={c}-{d:%m%d}-{t.replace(":","")} / {d:%m月%d日}({"月火水木金土日"[d.weekday()]}) {t}'
        for c, d, t in slots)
    return f"""あなたは「{cfg['clinic']['name']}」の集客担当です。{ch} 用の投稿を、下の投稿枠の数だけ作ってください。
枠ごとに切り口（悩み・季節・からだの仕組み・セルフケア・来院のきっかけ）を変え、同じ内容を繰り返さない。

{clinic_block(cfg)}

## 来週のテーマ
{theme}

## 調べた最新情報（使えるものだけ自然に活かす）
{notes}

## 書き方
{CHANNEL_GUIDE[ch]}

{rules_block()}

## 投稿枠
{slot_lines}

## 出力
次のJSONだけを出力する（前置き・説明・コードブロック記号は不要）。
{{"items": [{{"id": "枠のid", "topic": "テーマ一言", "title": "hpb_blogのみ。他は空文字",
  "text": "投稿本文", "headline": "画像見出し（instagram/gbpのみ）", "sub": "画像サブ", "tag": "画像タグ"}}]}}"""


def call_claude(prompt, model, tools=None, max_tokens=16000):
    import anthropic
    client = anthropic.Anthropic()
    msgs = [{"role": "user", "content": prompt}]
    kw = {"tools": tools} if tools else {}
    text = ""
    for _ in range(6):  # 検索の一時停止・長い応答の続きに対応
        r = client.messages.create(model=model, max_tokens=max_tokens, messages=msgs, **kw)
        text += "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        print(f"[claude] stop_reason={r.stop_reason} usage={getattr(r, 'usage', '')}")
        if r.stop_reason in ("pause_turn", "max_tokens"):
            msgs = msgs + [{"role": "assistant", "content": r.content}]
            if r.stop_reason == "max_tokens":
                msgs.append({"role": "user", "content": "続きをそのまま出力してください。"})
            continue
        break
    return text


def parse_json(text):
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    raw = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("---- 読み取れなかった返答（先頭/末尾） ----")
        print(text[:1500]); print("....."); print(text[-1500:])
        raise


def write_channel(cfg, ch, slots, theme, notes):
    """媒体ごとに生成。読み取りに失敗したら最大3回までやり直す"""
    last = None
    for attempt in range(3):
        try:
            text = call_claude(build_channel_prompt(cfg, ch, slots, theme, notes),
                               cfg["ai"]["model"], max_tokens=12000)
            return parse_json(text).get("items", [])
        except Exception as e:
            last = e
            print(f"[{ch}] {attempt+1}回目失敗: {e}")
    raise RuntimeError(f"{ch} の生成に3回失敗しました: {last}")


def ai_fix(cfg, item, issues):
    """NG表現をAIに直させる"""
    prompt = f"""次の{item['channel']}向け投稿文に、広告規制上NGの表現があります。
意味と魅力はできるだけ保ったまま、規制に沿う表現に書き直してください。
検出されたNG: {json.dumps(issues, ensure_ascii=False)}
禁止ルール:
{compliance.rules_as_prompt(item['channel'])}
他にも効果の断定・誇張・暗示があれば直す。書き直した本文だけを出力（説明不要）。

---
{item['text']}"""
    return call_claude(prompt, cfg["ai"]["review_model"], max_tokens=4000).strip()


def mock_plan(slots):
    items = []
    for ch, d, t in slots:
        items.append({"id": f"{ch}-{d:%m%d}-{t.replace(':','')}", "channel": ch, "topic": "冬の冷えと首こり",
                      "title": "寒くなると首がつらくなる理由", "headline": "朝、首が回らない日が増えたら",
                      "sub": "冷えで固まる「首まわり」をゆるめる1分ケア", "tag": "冬のからだ",
                      "text": "寒くなると首や肩がこわばりやすくなります。首の後ろを温めてから、ゆっくり呼吸を3回。"
                              "からだ全体から整えたい方は、三島駅南口徒歩3分のCreaへ。ご予約はホットペッパーかLINEから。"})
    return {"week_theme": "（テスト）冬の冷え", "research_notes": "テストモード", "items": items}


def main():
    cfg = config()
    today = now().date()
    start = today + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)  # 次の月曜
    if os.environ.get("START_DATE"):
        start = dt.date.fromisoformat(os.environ["START_DATE"])
    out_path = QUEUE / f"week-{start:%Y-%m-%d}.json"
    if out_path.exists() and os.environ.get("FORCE") != "1":
        print(f"既に作成済み: {out_path.name}"); return

    slots = week_slots(cfg, start)
    if DRY_RUN and not os.environ.get("ANTHROPIC_API_KEY"):
        plan = mock_plan(slots)
    else:
        theme, notes = research(cfg, start)
        print("テーマ:", theme)
        items_all, errors = [], []
        for ch in dict.fromkeys(c for c, _, _ in slots):
            try:
                got = write_channel(cfg, ch, [s for s in slots if s[0] == ch], theme, notes)
                items_all += [dict(it, channel=ch) for it in got]
            except Exception as e:
                errors.append(str(e))
        if errors:
            notify("一部の媒体の投稿を作れませんでした", "\n".join(errors))
        plan = {"week_theme": theme, "research_notes": notes, "items": items_all}

    by_id = {it.get("id"): it for it in plan["items"]}
    used = set()
    items, held = [], []
    for ch, d, t in slots:
        sid = f"{ch}-{d:%m%d}-{t.replace(':','')}"
        it = by_id.get(sid) if id(by_id.get(sid)) not in used else None
        if it is None:  # idがずれていても、同じ媒体の未使用の投稿を順に割り当てる
            it = next((x for x in plan["items"] if x["channel"] == ch and id(x) not in used), None)
        if not it:
            continue
        used.add(id(it))
        it = dict(it, id=sid, channel=ch)
        if not it.get("text"):
            continue
        hh, mm = map(int, t.split(":"))
        it["scheduled_at"] = dt.datetime(d.year, d.month, d.day, hh, mm,
                                         tzinfo=now().tzinfo).isoformat()
        full = (it.get("title", "") + "\n" + it["text"]) if ch == "hpb_blog" else it["text"]
        issues = compliance.check(full, ch)
        if issues and not (DRY_RUN and not os.environ.get("ANTHROPIC_API_KEY")):
            it["text"] = ai_fix(cfg, it, issues)
            full = (it.get("title", "") + "\n" + it["text"]) if ch == "hpb_blog" else it["text"]
            issues = compliance.check(full, ch)
        it["compliance"] = issues
        it["status"] = "held" if (issues and cfg["safety"]["hold_on_any_ng"]) else "pending"
        if it["status"] == "held":
            held.append(it)
        if ch in ("instagram", "gbp"):
            fn = f"{sid}-{start:%Y}.jpg"
            make_card(fn, it.get("headline") or it.get("topic", ""), it.get("sub", ""), it.get("tag", ""))
            it["image"] = fn
        items.append(it)

    save_json(out_path, {"week_start": str(start), "week_theme": plan.get("week_theme"),
                         "research_notes": plan.get("research_notes"), "items": items})

    lines = [f"来週（{start:%m/%d}〜）の投稿 {len(items)}件を作成し、予約しました。",
             f"週のテーマ: {plan.get('week_theme')}", "", "▼調べた最新情報", str(plan.get("research_notes")), ""]
    for it in items:
        mark = "⚠保留" if it["status"] == "held" else "予約"
        lines.append(f"[{mark}] {it['scheduled_at'][5:16]} {it['channel']} — {it.get('topic','')}")
    if held:
        lines += ["", "⚠保留の投稿はNG表現が残ったため自動投稿しません。GitHubの data/queue で直し、"
                      "status を pending に変えると投稿されます。"]
        for it in held:
            lines += [f"--- {it['id']} / NG: {[i['word'] for i in it['compliance']]}", it["text"]]
    lines += ["", "止めたい投稿があれば、その status を skip に変えてください。"]
    notify(f"来週の投稿{len(items)}件を予約しました", "\n".join(lines))


if __name__ == "__main__":
    main()
