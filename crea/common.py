import json, os, smtplib, datetime as dt
from email.mime.text import MIMEText
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
QUEUE = DATA / "queue"
IMAGES = DATA / "images"
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
