# Claude Code で使う（AIエコシステムの土台）

自動で回る部分（日曜の生成・予約投稿）はそのままに、Claude Code で手作業するときの
「ルール・権限・自動チェック・スキル・学び」を足したものです。

| 層 | ファイル | 役割 |
|---|---|---|
| ルール | `CLAUDE.md` | 仕組みの全体、正しい情報の置き場所、作業の流れ、広告ルール |
| 権限 | `.claude/settings.json` | `posts/` は自由に書ける。`config.yaml`・`crea/`・`data/queue/`・push・生成の実行は確認を取る |
| フック | `.claude/hooks/session_start.py` | 開始時に日付と直近の学びを渡す |
| フック | `.claude/hooks/block_secrets.py` | APIキー・トークン・`.env` の書き込みを止める |
| フック | `.claude/hooks/ad_check.py` | `posts/` と `data/queue/` の保存時に `crea/compliance.py` で法規チェック。NGなら書き直させる |
| スキル | `.claude/skills/crea-*` | 最新確認・来週分の確認・媒体別の作り方・広告チェック |
| 知識 | `knowledge/` | 広告ルールの根拠・学び・最新確認ログ |
| 出力 | `posts/` | 手で作った単発の投稿 |

## スキル
| 呼び方 | やること |
|---|---|
| `/crea-latest-check` | 媒体の仕様と広告ルールの変更を検索して記録 |
| `/crea-weekly-review` | 日曜に生成された来週分を公開前に確認・手直し |
| `/crea-gmap-post` | Googleマップ投稿を単発で作る |
| `/crea-hpb-blog` | HPBブログを単発で作る |
| `/crea-sns-post` | Instagram・Threads（instagram-agent-ja と併用） |
| `/crea-line-message` | LINE配信文 |
| `/crea-ad-review` | 7項目の広告チェックと言い換え |

## 必要なもの
Claude Code と python3（フックが `crea/compliance.py` を読み込みます。追加のインストールは不要）。
