"""法規チェック（あはき・柔整広告ガイドライン／薬機法／景品表示法／HPB登録不可ワード）

2段構え:
  1) ルールチェック … 決まったNG語を機械的に検出（確実・無料）
  2) AIチェック     … 言い回しの誇張・暗示をClaudeが確認し、安全な文に直す（generate.py側）
"""
import re

# どの媒体でもNG（効果の断定・最上級・保証・体験談・病名）
COMMON_NG = {
    "効果の断定": [r"治る", r"治す", r"治します", r"治せ", r"完治", r"根治", r"全快", r"効く", r"効きます",
                 r"効果があります", r"効果抜群", r"即効", r"必ず(良く|改善|楽)", r"改善します", r"解消します",
                 r"消えます", r"痩せ(る|ます)", r"若返", r"再発しない", r"予防でき"],
    "最上級・比較": [r"No\.?\s?1", r"ナンバーワン", r"日本一", r"県内一", r"地域一", r"三島一", r"業界初",
                 r"最高の", r"最上級", r"唯一", r"どこよりも", r"他院(より|と違)"],
    "保証・安全の断定": [r"100\s?[%％]", r"絶対", r"保証", r"副作用(なし|がない|ゼロ)", r"安全です", r"痛くない"],
    "体験談・口コミ": [r"お客様の声", r"患者様の声", r"体験談", r"ビフォー\s?アフター", r"Before\s?After",
                  r"喜びの声", r"口コミで(話題|人気)"],
    "病名・診断": [r"クローン病", r"潰瘍性大腸炎", r"糖尿病", r"がん(?!ば)", r"癌", r"うつ病", r"自律神経失調症",
               r"椎間板ヘルニア", r"脊柱管狭窄", r"リウマチ", r"不妊症", r"パニック障害", r"診断", r"処方"],
    "医療行為の表現": [r"治療", r"診療", r"患者"],
}

# ホットペッパービューティー専用（登録不可・警告ワード）
HPB_NG = {
    "HPB警告ワード": [r"鍼", r"はり治療", r"灸", r"医学", r"病院", r"医療", r"あん摩", r"マッサージ指圧",
                  r"整骨", r"接骨", r"施術所", r"症状"],
}

LIMITS = {"threads": 500, "instagram": 2200, "gbp": 1500, "line_broadcast": 5000, "hpb_blog": 10000}


def check(text: str, channel: str) -> list[dict]:
    """NG表現の一覧を返す。空なら合格。"""
    rules = dict(COMMON_NG)
    if channel == "hpb_blog":
        rules.update(HPB_NG)
    issues = []
    for category, patterns in rules.items():
        for p in patterns:
            for m in re.finditer(p, text, flags=re.IGNORECASE):
                issues.append({"category": category, "word": m.group(0), "pos": m.start()})
    limit = LIMITS.get(channel)
    if limit and len(text) > limit:
        issues.append({"category": "文字数オーバー", "word": f"{len(text)}文字（上限{limit}）", "pos": -1})
    return issues


def _readable(p: str) -> str:
    p = re.sub(r"\(\?[!<=][^)]*\)", "", p)          # 先読み等を除去
    p = p.replace("\\s?", "").replace("\\.?", ".").replace("\\", "")
    p = re.sub(r"\[([^\]]*)\]", lambda m: m.group(1)[0], p)
    return re.sub(r"\(([^)]*)\)", lambda m: "〜" + "/".join(m.group(1).split("|")), p)


def rules_as_prompt(channel: str, hpb_only: bool = False) -> str:
    """AIに渡す禁止ルールの説明文"""
    rules = dict(HPB_NG) if hpb_only else dict(COMMON_NG)
    if channel == "hpb_blog" and not hpb_only:
        rules.update(HPB_NG)
    return "\n".join(f"- {cat}: " + "、".join(_readable(p) for p in pats) for cat, pats in rules.items())
