import json, os, re, smtplib, datetime as dt
from email.mime.text import MIMEText
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
QUEUE = DATA / "queue"
IMAGES = DATA / "images"
LOG = DATA / "log"
KNOWLEDGE = ROOT / "knowledge"
JST = dt.timezone(dt.timedelta(hours=9))
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"


def now() -> dt.datetime:
    return dt.datetime.now(JST)


def config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def knowledge_text(name: str) -> str:
    """knowledge/<name> の全文（なければ空）"""
    f = KNOWLEDGE / name
    return f.read_text(encoding="utf-8") if f.exists() else ""


def knowledge_tail(name: str, n: int = 20) -> str:
    """knowledge/<name> の箇条書き（- で始まる行）の最後の n 行"""
    lines = [l.rstrip() for l in knowledge_text(name).splitlines() if l.strip().startswith("- ")]
    return "\n".join(lines[-n:])


def clean_text(t: str) -> str:
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


def all_queue_items():
    """(ファイルパス, 中身) を全部返す"""
    for f in sorted(QUEUE.glob("*.json")):
        yield f, load_json(f, {"items": []})


def image_public_url(filename: str) -> str:
    base = os.environ.get("IMAGE_BASE_URL")
    if not base:
        repo = os.environ.get("GITHUB_REPOSITORY", "OWNER/REPO")
        branch = os.environ.get("GITHUB_REF_NAME", "main")
        base = f"https://raw.githubusercontent.com/{repo}/{branch}/data/images"
    return f"{base.rstrip('/')}/{filename}"


def notify(subject: str, body: str):
    """オーナーにメールで知らせる（Gmailのアプリパスワードを使用）"""
    to = os.environ.get("NOTIFY_EMAIL")
    user = os.environ.get("GMAIL_USER")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    print(f"\n===== 通知: {subject} =====\n{body}\n")
    if DRY_RUN or not (to and user and pw):
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"【Crea自動集客】{subject}"
    msg["From"] = user
    msg["To"] = to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.send_message(msg)
