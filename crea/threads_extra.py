"""Threadsの追加投稿（1日10本）
朝8:30の本投稿（3日セットのA/B/C/D）はそのまま。同じ日のテーマで、2時間おきの追加投稿を自動で作って予約する。
- 30分ごとの予約投稿の実行（crea.publish）の最初に呼ばれ、2日先までの分を1日1回のAI呼び出しで作る
- 作った投稿は本投稿と同じ週のファイルに入れる（広告ルールのチェック → AIで修正 → それでもNGなら保留）
"""
import datetime as dt, json
from .common import config, now, all_queue_items, save_json, notify
from . import compliance

# 追加投稿の時刻と役割（本投稿8:30と合わせて1日10本・2時間おき）
EXTRA = [
    ("6:30",  0, "朝のひとこと。起きた瞬間のからだの心の声に共感する短文（60〜120字）"),
    ("10:30", 0, "本投稿のテーマについての、小さな気づき1つ（120〜200字）"),
    ("12:30", 0, "昼休みにできるセルフケア1つ。手順は2〜3行で（150〜250字）"),
    ("14:30", 0, "よくある質問1つにQ&Aで答える。断定せず、からだの仕組みで説明（150〜250字）"),
    ("16:30", 0, "からだの仕組みを身近なたとえ話で1つ（120〜220字）"),
    ("18:30", 0, "夕方の疲れ・帰り道の心の声への共感。否定せず、頑張りを肯定する（100〜200字）"),
    ("20:30", 0, "思い込みを静かに崩す一言（「年齢のせい」「我慢するしかない」など）。数字や断言は使わない（120〜220字）"),
    ("22:30", 0, "寝る前にできる呼吸かストレッチ1つ（100〜200字）"),
    ("0:30",  1, "1日のしめくくり。明日の本投稿のテーマを予告し、「当てはまる人はコメントで教えてください」と結ぶ（80〜160字）"),
]


def _prompt(cfg, main, day, nxt):
    from .generate import clinic_block, strategy_block, rules_block
    roles = "\n".join(f"- id=threads-{day:%m%d}-x{t.replace(':','')} / {t} / 役割: {r}" for t, _, r in EXTRA)
    return f"""あなたは「{cfg['clinic']['name']}」のThreads担当です。
今日（{day:%m月%d日}）の本投稿は下のとおりです。このテーマに沿って、同じ日に流す追加投稿を{len(EXTRA)}本作ってください。

## 今日の本投稿（テーマの軸。言い回しは繰り返さない）
{main['text']}

## 明日の本投稿のテーマ（0:30の予告に使う）
{nxt or '（未定。予告は「明日もからだの話をします」程度にする）'}

{clinic_block(cfg)}

{strategy_block(cfg)}

## 書き方（全投稿共通）
- 話し言葉で1文を短く、1〜2行ごとに改行。宣伝色は薄く、URLは書かない。ハッシュタグは付けない
- 1投稿に1つのことだけ。同じ書き出し・同じ締めを繰り返さない
- お客様の声・体験談・実在しない出来事や数字は書かない

{rules_block()}

## 投稿枠
{roles}

## 出力
次のJSONだけを出力する（前置き・説明不要）。
{{"items": [{{"id": "枠のid", "topic": "一言", "text": "投稿本文"}}]}}"""


def fill(cfg=None, days_ahead=2):
    cfg = cfg or config()
    tc = cfg["channels"]["threads"]
    if not tc.get("enabled") or tc.get("posts_per_day", 1) <= 1:
        return
    from .generate import call_claude, parse_json, ai_fix
    t = now()
    files = list(all_queue_items())
    mains = {}
    for path, q in files:
        for it in q["items"]:
            if it["channel"] == "threads" and not it.get("extra_of"):
                mains[dt.datetime.fromisoformat(it["scheduled_at"]).date()] = (path, q, it)
    has_extra = {it.get("extra_of") for _, q in files for it in q["items"] if it.get("extra_of")}
    for day in sorted(mains):
        if not (t.date() <= day <= t.date() + dt.timedelta(days=days_ahead)):
            continue
        path, q, main = mains[day]
        if main["id"] in has_extra or "extras" in main:
            continue
        nxt = mains.get(day + dt.timedelta(days=1))
        try:
            text = call_claude(_prompt(cfg, main, day, nxt[2]["text"][:300] if nxt else ""),
                               cfg["ai"]["model"], max_tokens=8000)
            got = {x["id"]: x for x in parse_json(text).get("items", [])}
        except Exception as e:
            notify("Threadsの追加投稿を作れませんでした", f"{day}: {e}")
            continue
        added = 0
        for hhmm, plus, _ in EXTRA:
            iid = f"threads-{day:%m%d}-x{hhmm.replace(':','')}"
            x = got.get(iid)
            if not x or not x.get("text"):
                continue
            h, m = map(int, hhmm.split(":"))
            when = dt.datetime.combine(day + dt.timedelta(days=plus), dt.time(h, m), tzinfo=t.tzinfo)
            if when <= t:
                continue  # 過ぎた時刻の分は作らない
            item = {"id": iid, "channel": "threads", "extra_of": main["id"], "topic": x.get("topic", ""),
                    "title": "", "text": x["text"].strip(), "scheduled_at": when.isoformat(),
                    "status": "pending", "compliance": []}
            ng = compliance.check(item["text"], "threads")
            if ng:
                try:
                    item["text"] = ai_fix(cfg, item, ng)
                    ng = compliance.check(item["text"], "threads")
                except Exception:
                    pass
            if ng:
                item.update(status="held", compliance=ng)
            q["items"].append(item)
            added += 1
        # 本投稿にも「追加済み」の印をつける（追加が0本でも同じ日を何度も作り直さない）
        main.setdefault("extras", added)
        q["items"].sort(key=lambda x: x["scheduled_at"])
        save_json(path, q)
        has_extra.add(main["id"])
        print(f"Threads追加投稿: {day} に {added}本")


if __name__ == "__main__":
    fill()
