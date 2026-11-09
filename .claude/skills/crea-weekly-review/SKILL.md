---
name: crea-weekly-review
description: 日曜に自動生成された来週分の予約投稿（data/queue/week-*.json）を、公開前に確認・手直しする。「来週の投稿を見て」「予約を確認」「今週の投稿チェック」と言われた時、月曜朝の定期実行で使う。
---

# 来週分の予約投稿の確認・手直し

## 手順
1. `git pull` で最新にし、いちばん新しい `data/queue/week-YYYY-MM-DD.json` を開く
2. `/crea-latest-check` で、生成後に媒体の仕様や広告ルールが変わっていないか確認
3. `data/performance.json` と `knowledge/learnings.md` から、先週伸びた型・伸びなかった型を1行ずつ
4. `status: "pending"` の各投稿を、次の観点で見る
   - 事実が `config.yaml` と合っているか（住所・時間・メニュー名）
   - 天気・行事など日付のある情報が、公開日時点で古くならないか
   - `/crea-ad-review` の7項目
   - 1行目（Googleマップ・HPBは冒頭2行）で誰向けか分かるか
5. 一覧表で出す：`id`／媒体／公開日時／判定（OK・要修正・保留）／理由

## 直すとき
- `data/queue/` の編集は自動公開に直結するので、直した文を見せて確認を取ってから保存する
- 保存するとフックが `crea/compliance.py` で再チェックする。NGなら直す
- 公開を止めたい投稿は `status` を変える前に、`crea/publish.py` がどの値を見ているか確認する

## 最後に
直した理由のうち次も使えるものを `knowledge/learnings.md` に追記する。
