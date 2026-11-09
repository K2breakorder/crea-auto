---
name: crea-latest-check
description: Googleマップ・ホットペッパービューティー・Instagram・Threads・LINEの投稿を作る前に、媒体の仕様変更と広告ルール（あはき法・景表法・薬機法）の最新情報を検索して確認する。投稿づくりの最初に必ず使う。
---

# 最新情報の確認（投稿前に毎回）

※ 日曜の自動生成（crea/generate.py）でも検索は行われる。このスキルは Claude Code で手作業するとき用。

## 手順
1. `knowledge/latest-check-log.md` の最終確認日を見る。同じ媒体で7日以内なら、手順3だけでよい。
2. 次を Web 検索で確認する（媒体ごとに1〜2回。今年の年号を入れる）。
   - Googleビジネスプロフィール：投稿の種類・文字数・写真サイズ・不承認の理由の変更（support.google.com/business を優先）
   - ホットペッパービューティー：ブログ・クーポン・掲載基準の変更（SALON BOARD のお知らせ）
   - Instagram / Threads：アルゴリズム・機能の変更（Meta 公式の発表を優先）
   - 広告ルール：厚労省「あはき・柔整広告ガイドライン」の改定、静岡県・三島市保健所の指導情報、景表法・ステマ規制の動き
3. 変わった点だけを `knowledge/latest-check-log.md` に追記する：
   `- YYYY-MM-DD [媒体] 変更内容（出典URL）`
4. 規制に関わる変更なら `knowledge/regulations.md` と `crea/compliance.py`（NG語の唯一のリスト）の更新を提案する（勝手に変えず、確認を取る）。

## 出し方
今回の投稿に効く変更を最大3点、1行ずつ伝えてから投稿づくりに進む。変更がなければ「変更なし（確認日）」と1行だけ。
