---
name: crea-sns-post
description: CreaのInstagram（フィード・リール・カルーセル）とThreadsの投稿を作る。「インスタ投稿」「Threads」「リール」と言われた時に使う。細部は instagram-agent-ja の各スキルに任せる。
---

# Instagram・Threads 投稿

## 先にやること
1. `/crea-latest-check`（Instagram・Threads）
2. `knowledge/learnings.md` の SNS の学びを読む

## 使い分け
| 作るもの | 使うスキル |
|---|---|
| リール台本 | `instagram-agent-ja:ig-reel` |
| カルーセル | `instagram-agent-ja:ig-carousel` |
| キャプション | `instagram-agent-ja:ig-caption` |
| 仕上げ（AIっぽさを消す） | `instagram-agent-ja:ig-human` |
| 振り返り | `instagram-agent-ja:ig-audit` |

## Crea の決まり
- テーマは「セルフケアの知識」「院の日常」「施術の流れ」の3本柱。効果を約束する話はしない
- 1投稿1テーマ。最後のお願いは1つ（保存／プロフィールのリンクから予約／LINE登録のどれか）
- Threads はインスタの要点を150〜300字の会話調に直す。ハッシュタグは1つまで
- ハッシュタグは3つ前後：#三島 #三島駅南口 ＋ テーマの言葉
- お客様の写真・声は、書面の同意がある時だけ

## 保存
`posts/instagram/` または `posts/threads/` に `YYYY-MM-DD_<題名>.md`。フックが `crea/compliance.py` で広告チェック、最後に `/crea-ad-review`。
