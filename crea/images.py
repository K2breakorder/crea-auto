"""投稿用画像（1080x1350・ブラウン系）を自動で作る"""
from PIL import Image, ImageDraw, ImageFont
from .common import IMAGES

W, H = 1080, 1350
BG = (246, 239, 230)       # ベージュ
DARK = (92, 64, 45)        # ダークブラウン
ACCENT = (166, 124, 82)    # キャメル
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
]


def _font(size, bold=True):
    paths = FONT_CANDIDATES if bold else FONT_CANDIDATES[1:] + FONT_CANDIDATES[:1]
    for p in paths:
        try:
            return ImageFont.truetype(p, size, index=0)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        if draw.textlength(cur + ch, font=font) > max_w and cur:
            # 句読点・閉じ括弧は行頭に置かない
            if ch in "、。」）！？ー":
                cur += ch; lines.append(cur); cur = ""; continue
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def _balanced(draw, text, font, max_w):
    """行の長さをそろえて、1〜2文字だけの行（泣き別れ）を防ぐ"""
    lines = _wrap(draw, text, font, max_w)
    if len(lines) > 1 and "\n" not in text:
        total = draw.textlength(text, font=font)
        target = total / len(lines) * 1.12
        alt = _wrap(draw, text, font, min(max_w, target))
        if len(alt) == len(lines):
            lines = alt
    return lines


def make_card(filename: str, headline: str, sub: str = "", tag: str = "") -> str:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    m = 100
    d.rectangle([40, 40, W - 40, H - 40], outline=ACCENT, width=3)
    # 見出しは長さに応じて文字サイズを調整
    size = 96 if len(headline) <= 14 else 84 if len(headline) <= 22 else 72
    f_h, f_s, f_tag = _font(size), _font(46, bold=False), _font(38)
    h_lines = _balanced(d, headline, f_h, W - m * 2)[:5]
    s_lines = _balanced(d, sub, f_s, W - m * 2)[:5] if sub else []
    lh_h, lh_s = int(size * 1.42), 74
    block = (100 if tag else 0) + len(h_lines) * lh_h + (110 + len(s_lines) * lh_s if s_lines else 0)
    top, bottom = 80, H - 200
    y = top + max(40, (bottom - top - block) // 2)
    if tag:
        tw = d.textlength(tag, font=f_tag)
        d.rounded_rectangle([m, y, m + tw + 52, y + 64], radius=32, fill=ACCENT)
        d.text((m + 26, y + 9), tag, font=f_tag, fill=(255, 255, 255))
        y += 100
    for line in h_lines:
        d.text((m, y), line, font=f_h, fill=DARK)
        y += lh_h
    if s_lines:
        d.line([m, y + 20, m + 160, y + 20], fill=ACCENT, width=6)
        y += 80
        for line in s_lines:
            d.text((m, y), line, font=f_s, fill=DARK)
            y += lh_s
    d.rectangle([40, H - 200, W - 40, H - 40], fill=DARK)
    d.text((m, H - 175), "Crea athlete & beauty care", font=_font(46), fill=(255, 255, 255))
    d.text((m, H - 110), "三島駅南口 徒歩3分｜完全予約制・1対1", font=_font(34, bold=False), fill=(235, 220, 200))
    IMAGES.mkdir(parents=True, exist_ok=True)
    path = IMAGES / filename
    img.save(path, "JPEG", quality=90)
    return str(path)
