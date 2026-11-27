---
name: crea-agent-launch
description: Creaの仕事を「自分専用のAIエージェント」にして、Claude Managed Agents で定期的に自動で動かすときの入口。Anthropic公式の /launch-your-agent をCreaの前提（広告ルール・下書き止まり・公開リポジトリ）つきで始める。「エージェントを作りたい」「これを毎週自動でやらせたい」「launch-your-agent」と言われた時に使う。
---

# Crea用エージェントの立ち上げ

中身は Anthropic 公式スキル `/launch-your-agent`（https://github.com/anthropics/launch-your-agent ）。
このスキルは、その前にCreaの前提をそろえるための入口です。

## 始める前に院長へ伝えること（1回だけ・短く）
- Anthropic の APIキー（platform.claude.com）が必要。キーはチャットに貼らず `my-agent/.env` に入れる
- `my-agent/` は `.gitignore` 済み。このリポジトリは公開なので、鍵やお客様の情報は絶対にコミットしない
- 動かすたびに少額のAPI料金がかかる

## Creaで最初に作る候補（院長に選んでもらう）
| 候補 | やること | 出力 | 既存の仕組みとの関係 |
|---|---|---|---|
| A. 週次の数字ウォッチャー | 毎週、Instagram・Threads・Googleマップの数字（`data/performance.json`）を読み、伸びた型・止める型を3行で出す | 院長へのメール下書き | 読むだけ。`crea/` には触らない |
| B. 公開前の広告チェック係 | `data/queue/` の来週分を読み、広告ルール7項目で点検して直し案を出す | 直し案の一覧（下書き） | 直すのは院長確認後。自動で書き換えない |
| C. LINE・メールの返信下書き係 | よくある質問への返信案を作る（`customer-support-agent` の型を参考） | 返信の下書きのみ | 送信はしない |

## 守ること（launch-your-agent の各段階で毎回あてはめる）
- 出力は **下書き止まり**（送信・投稿・予約変更はしない。必要なら `always_ask`）
- 事実は `config.yaml` と `knowledge/` だけから。料金・実績・経歴（業界歴35年など）は書かない
- 効果の約束・お客様の声・ビフォーアフターは使わない（`knowledge/regulations.md`）
- 定時実行は Managed Agents のスケジュールを使う。GitHub の定時実行（schedule）は遅れ・飛びが出たので使わない
- 既存の `crea/`・`.github/workflows/`・`config.yaml` は変えない

## 進め方
1. 上の候補を AskUserQuestion で選んでもらう
2. `/launch-your-agent` を起動し、聞き取りの最初の答えとして選んだ候補と「守ること」を渡す
3. 終わったら `/wrap-up`。できたエージェント名・IDの置き場所（`my-agent/`）を `knowledge/learnings.md` に1行
