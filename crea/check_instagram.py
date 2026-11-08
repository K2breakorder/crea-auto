"""Instagram接続テスト：トークンでアクセスできるアカウントとIDを調べる（トークン自体は表示しない）"""
import os, requests

V = os.environ.get("IG_API_VERSION", "v23.0")
tok = os.environ.get("IG_ACCESS_TOKEN", "")
print("トークンの種類（先頭4文字）:", tok[:4], "/ 長さ:", len(tok))

checks = [
    ("IGログイン方式 /me", f"https://graph.instagram.com/{V}/me", {"fields": "user_id,username,account_type"}),
    ("FB方式 /me", f"https://graph.facebook.com/{V}/me", {"fields": "id,name"}),
    ("FB方式 ページ経由", f"https://graph.facebook.com/{V}/me/accounts",
     {"fields": "name,instagram_business_account{id,username}"}),
    ("FB方式 ビジネス経由", f"https://graph.facebook.com/{V}/me/businesses",
     {"fields": "id,name,owned_instagram_accounts{id,username},instagram_accounts{id,username}"}),
]
for name, url, params in checks:
    try:
        r = requests.get(url, params=dict(params, access_token=tok), timeout=30)
        body = r.text.replace(tok, "***")[:800]
        print(f"\n== {name}: HTTP {r.status_code}\n{body}")
    except Exception as e:
        print(f"\n== {name}: 例外 {e}")
