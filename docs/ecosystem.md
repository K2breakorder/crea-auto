# CreaのAIエコシステム（全体の地図）

依頼が入ってから、投稿が出て、数字が次の企画に戻るまでを7つの段で整理したものです。
それぞれの段が、このリポジトリのどのファイルにあたるかを書いています。

| 段 | Creaでの中身 | 場所 |
|---|---|---|
| ①人 | オーナー。方針を決める、指摘する、止める・直すの最終判断 | 指摘は `knowledge/feedback.md` に残る |
| ②入口 | PCの Claude Code／スマホの Claude アプリ／届いたメールを見て GitHub で `status` を書き換える | `CLAUDE.md`、`.claude/` |
| ③司令塔 | Claude Code。毎回ルールを読み、書いたら点検し、指摘をメモに残す | `CLAUDE.md`、`.claude/hooks/`、`.claude/settings.json` |
| ④振り分け | 調べる／作る／出す／記録する／予約につなげる | 下の表 |
| ⑤⑥担当とツール | 下の表 | `crea/`、`.github/workflows/`、`.claude/skills/` |
| ⑦出口 | Instagram・Threads・Googleマップ・LINE（自動）、HPBブログ・アメブロ（原稿メール）→ 予約はホットペッパーとLINE | `crea/publishers.py` |

## 5つの担当

| 担当 | いつ | やること | 場所 |
|---|---|---|---|
| 調べる | 日曜 18:17／手作業の前 | 三島の天気・行事、話題、媒体の仕様、広告ルール、上位院の動き | `crea/generate.py` の research、`/crea-latest-check` |
| 作る | 日曜 18:17／単発 | 冒頭フックの型から1行目 → 本文 → 画像 | `crea/generate.py`、`crea/images.py`、`/crea-sns-post` ほか |
| 出す | 30分ごと | 予約時刻を過ぎた投稿を公開。直前にもう一度チェック、同じ文は出さない | `crea/publish.py` |
| 記録する | 毎晩 22:03 | 数字を集め、一覧と推移を保存し、まとめをメール | `crea/report.py`、`data/log/` |
| 予約につなげる | 毎回 | 本文の最後にホットペッパーとLINE。GoogleマップのボタンはLINE | `config.yaml`、`crea/lint.py` が抜けを点検 |

## ルールと記録（毎回読むもの）

| 何 | 場所 | 誰が読むか |
|---|---|---|
| 書き方のルール集 | `CLAUDE.md`、`knowledge/regulations.md` | Claude Code |
| 冒頭フックの型 | `knowledge/hooks.md` | 毎週の自動生成、Claude Code |
| 点検スクリプト（NG語） | `crea/compliance.py` | 生成時・公開直前・保存時のフック |
| 点検スクリプト（構成・決めごと・重複） | `crea/lint.py` | 生成時、`python3 -m crea.lint` |
| 前回の指摘メモ | `knowledge/feedback.md` | 毎週の自動生成、セッション開始時 |
| 学び | `knowledge/learnings.md` | 毎週の自動生成、セッション開始時 |
| 過去の投稿と数字 | `data/performance.json`、`data/log/posts.csv` | 毎週の自動生成（伸びた型を増やす） |

## 安全の線

| 線 | 仕組み |
|---|---|
| NG表現が残ったら出さない | `safety.hold_on_any_ng`（保留にしてメール） |
| 同じ投稿を2回出さない | 投稿ごとに印を保存。同じ媒体・同じ文は `duplicate` で見送り。生成時にも過去60日と比べる |
| 鍵・パスワードを書かない | `.claude/hooks/block_secrets.py`、GitHub Secrets |
| お金がかかること・予約中の書き換えは確認 | `.claude/settings.json` の `ask` |
| 暴走を防ぐ | 1日の上限（`safety.max_posts_per_day`）、12時間以上遅れた投稿は出さない |
| お客様の情報を置かない | 公開リポジトリのため、個人情報・写真は置かない |

## 数字が次の企画へ戻る流れ

```
投稿（hook の番号つき）→ 毎晩 report.py が数字を集める → performance.json
   → 日曜 generate.py が「好調・不調」「型ごとの平均」「指摘メモ」「学び」を読んで来週分を作る
```

## ふだん見るもの
- 毎晩のメール「今日のまとめ」：今日出た投稿、止まっている投稿、伸びた投稿、明日の予定
- 日曜のメール「来週の投稿を予約しました」：一覧と、点検で気になった点
- `data/log/posts.csv`：全投稿の一覧（Googleスプレッドシートに読み込めます）
- メールを減らしたい時：`config.yaml` の `report.only_when_needed: true`
