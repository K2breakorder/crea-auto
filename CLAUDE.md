# Crea 集客オートパイロット — Claude Code 用ルール

このリポジトリは「Crea athlete & beauty care」（三島駅南口 徒歩3分／鍼灸・整体・美容ケア）の
集客投稿を自動で作り、法規チェックをして、各媒体へ予約投稿する仕組みです。
Claude Code で作業するときは、まずこのファイルを守ってください。

## 1. 仕組みの全体（すでに自動で動いている部分）
| いつ | 何が | どこ |
|---|---|---|
| 毎週日曜 18:17 | 反応を集める → 最新情報を検索 → 来週分を作成 → 法規チェック → 画像作成 → メール | `.github/workflows/weekly-generate.yml` → `crea/insights.py` `crea/generate.py` |
| 30分ごと | 予約時刻を過ぎた投稿を公開 | `publish.yml` → `crea/publish.py` |
| 月2回 | Instagram・Threadsのトークン更新 | `refresh-tokens.yml` |

- 作られた投稿の予約一覧：`data/queue/week-YYYY-MM-DD.json`（`items[]` の `status` が `pending` のものがこれから公開される）
- 反応の記録：`data/performance.json`
- 投稿画像：`data/images/`

## 2. 正しい情報の置き場所（ここ以外から事実を作らない）
- 院の住所・時間・電話・メニュー・強み・ターゲット・投稿枠：**`config.yaml`**
- 法規チェックのNG語：**`crea/compliance.py`**（ここが唯一の正。フックもこれを使う）
- 広告ルールの説明と根拠：`knowledge/regulations.md`
- 学び：`knowledge/learnings.md`／最新確認の記録：`knowledge/latest-check-log.md`

## 3. Claude Code での作業の流れ
1. **最新確認**：`/crea-latest-check`（媒体の仕様と広告ルールの変更）
2. **振り返り**：`knowledge/learnings.md` と `data/performance.json` を見て、前回より1つ以上良くする
3. **作る・直す**：
   - 来週分の自動生成を確認・手直し → `/crea-weekly-review`
   - 単発の投稿 → `/crea-gmap-post` `/crea-hpb-blog` `/crea-sns-post` `/crea-line-message`（保存先は `posts/<媒体>/`）
4. **チェック**：`/crea-ad-review`。保存時にはフックが `crea/compliance.py` で自動チェックする
5. **学びを残す**：`knowledge/learnings.md` に1〜3行

## 4. 広告ルールの要点（厚労省 あはき・柔整広告ガイドライン 2025-02-18 ほか）
- 効果を約束しない（治る・効く・改善します）。症状名＋効く、と読める書き方をしない
- 技能・経歴の強調、No.1・唯一などの比較、絶対・保証はしない
- 診療・診察・初診・往診・治療・患者・保険取扱い・交通事故取扱いは使わない（治療→施術、患者→お客様、初診→初回）
- お客様の声・ビフォーアフターは使わない。Google口コミのお願いは特典と引き換えにしない
- HPBは「鍼」「灸」「症状」「施術所」なども登録不可ワード（compliance.py の HPB_NG）
- 迷ったら書かない。「お気軽にご相談ください」で締める

## 5. 触るときに確認を取るもの
- `config.yaml`、`crea/`、`.github/workflows/`、`data/queue/`（予約中の投稿は自動公開されるため）
- `python -m crea.generate` の実行（Claude API の料金がかかる）
- `git push`（毎回確認。force push はしない）

## 6. 安全
- APIキー・トークンはファイルに書かない（GitHub Secrets のみ）。フック block_secrets が止める
- このリポジトリは公開（Public）。お客様の個人情報・写真は置かない
