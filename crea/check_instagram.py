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
checks.append(("トークンの許可情報", f"https://graph.facebook.com/{V}/debug_token", {"input_token": tok}))
for name, url, params in checks:
    try:
        r = requests.get(url, params=dict(params, access_token=tok), timeout=30)
        body = r.text.replace(tok, "***")[:800]
        print(f"\n== {name}: HTTP {r.status_code}\n{body}")
    except Exception as e:
        print(f"\n== {name}: 例外 {e}")

# 自動検出したIDでアカウント名を確認（publishers.ig_user_id と同じ考え方）
try:
    d = requests.get(f"https://graph.facebook.com/{V}/debug_token",
                     params={"input_token": tok, "access_token": tok}, timeout=30).json().get("data", {})
    ids = [t for sc in d.get("granular_scopes", [])
           if sc.get("scope") in ("instagram_content_publish", "instagram_basic") for t in sc.get("target_ids", [])]
    for iid in dict.fromkeys(ids):
        r = requests.get(f"https://graph.facebook.com/{V}/{iid}",
                         params={"fields": "id,username", "access_token": tok}, timeout=30)
        print("\n== 自動検出したInstagramアカウント:", r.text.replace(tok, "***")[:300])
    if not ids:
        print("\n== 自動検出できず: granular_scopes にInstagramの対象IDがありません")
except Exception as e:
    print("\n== 自動検出できず:", e)
