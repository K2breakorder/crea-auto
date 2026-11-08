"""Instagram・Threadsの長期トークン（60日で失効）を自動更新し、GitHub Secretsを書き換える
（月2回実行）"""
import os, subprocess, requests
from .common import notify, DRY_RUN

TARGETS = [
    ("IG_ACCESS_TOKEN", "https://graph.instagram.com/refresh_access_token", "ig_refresh_token"),
    ("THREADS_ACCESS_TOKEN", "https://graph.threads.net/refresh_access_token", "th_refresh_token"),
]


def main():
    errors = []
    for secret, url, grant in TARGETS:
        tok = os.environ.get(secret)
        if not tok:
            continue
        if DRY_RUN:
            print("DRY_RUN:", secret); continue
        r = requests.get(url, params={"grant_type": grant, "access_token": tok}, timeout=30)
        if not r.ok or "access_token" not in r.json():
            errors.append(f"{secret}: {r.text[:300]}"); continue
        subprocess.run(["gh", "secret", "set", secret, "--body", r.json()["access_token"]], check=True)
        print("更新:", secret)
    if errors:
        notify("トークン更新に失敗しました", "\n".join(errors) +
               "\n\n手順書の『トークンの取り直し』で再発行してください。")


if __name__ == "__main__":
    main()
