# Crea 集客オートパイロット — セットアップ手順書

毎週日曜の夕方に **最新情報を調べて来週1週間分の投稿を自動で作り、法規チェックをして、予約時刻に各媒体へ自動投稿** します。
反応（保存・シェア・コメント）を毎週集めて、伸びた型を次の週に増やすので、回すほど精度が上がります。

## 全体の流れ

```
日曜 18:17  ① 先週の反応を集める（Instagram・Threads）
            ② 最新情報を検索（三島の天気・行事、40〜60代女性の話題、各SNSの運用動向）
            ③ 来週分を作成（Instagram 3 / Threads 7 / Googleマップ 2 / HPBブログ 2 / LINE 月1）
            ④ 法規チェック（NG語の機械チェック → AIで書き直し → 再チェック）
            ⑤ ブラウン系の投稿画像を自動作成
            ⑥ 予約一覧をメールでお知らせ
30分ごと    ⑦ 予約時刻を過ぎた投稿を自動で公開
月2回       ⑧ Instagram・Threadsの鍵（トークン）を自動更新
```

| 媒体 | 自動投稿 | 補足 |
|---|---|---|
| Instagram | ○ | 画像＋キャプション |
| Threads | ○ | テキスト |
| Googleマップ（ビジネスプロフィール） | ○ | Googleの API 利用申請が通るまでは原稿をメールで届けます |
| LINE一斉配信 | ○ | 送る前に残り通数を確認。足りなければ自動で見送り |
| ホットペッパー | △ | HPB には投稿用の API がないため、完成原稿をメールで届けます（貼り付け約1分） |

## かかる費用の目安（月額）

| 項目 | 費用 |
|---|---|
| GitHub（自動実行の場所） | 0円（公開リポジトリ） |
| Claude API（文章づくり＋検索） | 数百円〜1,500円程度（使った分だけ。上限設定可） |
| Instagram / Threads / Googleの API | 0円 |
| LINE | 0円（無料プランの月200通以内） |

---

## セットアップ（初回のみ・約2〜3時間）

### 1. GitHub にこのフォルダを置く
1. https://github.com でアカウント作成
2. 右上「＋」→ **New repository** → 名前 `crea-auto` → **Public** を選ぶ → Create
   - 投稿画像をInstagramに渡すため公開にします。パスワード類は手順3の「Secrets」に入れるので公開されません。
3. 「uploading an existing file」から、このフォルダの中身を全部ドラッグして **Commit changes**
   - `.github` フォルダも必ず含めてください（見えない場合はPCで「隠しファイルを表示」）

### 2. 各サービスの鍵を取る

**① Claude API（必須）**
1. https://console.anthropic.com に登録 → Billing でクレジット購入（$10〜で十分）
2. Settings → Limits で月の上限を設定（例：$15）すると安心
3. API Keys → Create Key → コピー → `ANTHROPIC_API_KEY`

**② お知らせメール（必須）**
1. Googleアカウントで2段階認証をON
2. https://myaccount.google.com/apppasswords で「アプリパスワード」を作成（16桁）
3. `GMAIL_USER`＝送信に使うGmail、`GMAIL_APP_PASSWORD`＝16桁、`NOTIFY_EMAIL`＝受け取るアドレス

**③ Instagram**
1. Instagram をプロアカウント（ビジネス）に切り替え
2. https://developers.facebook.com でアプリ作成 → 「Instagram API（Instagramログイン）」を追加
3. 「アプリの役割」で自分のInstagramをテスターに追加し、Instagram側で承認
4. 権限 `instagram_business_basic` `instagram_business_content_publish` でトークンを生成
5. 長期トークン → `IG_ACCESS_TOKEN`、InstagramのユーザーID → `IG_USER_ID`
   - 自分のアカウントだけに投稿する使い方なので、通常はアプリ審査なしで使えます

**④ Threads**
1. 同じMetaアプリに「Threads API」を追加 → 自分をThreadsテスターに追加
2. 権限 `threads_basic` `threads_content_publish` `threads_manage_insights` でトークン生成
3. 長期トークン → `THREADS_ACCESS_TOKEN`、ユーザーID → `THREADS_USER_ID`

**⑤ Googleマップ（ビジネスプロフィール）**
1. https://console.cloud.google.com でプロジェクト作成
2. Google の「Business Profile API アクセス申請フォーム」から利用申請（審査に数日〜数週間）
3. 承認後、「My Business Account Management API」「Google My Business API」を有効化
4. OAuth クライアントを作成し、リフレッシュトークンを取得
5. `GBP_CLIENT_ID` `GBP_CLIENT_SECRET` `GBP_REFRESH_TOKEN` `GBP_ACCOUNT_ID` `GBP_LOCATION_ID`
   - **申請が通るまでは空欄でOK。** その間は投稿文がメールで届くので、Googleマップのアプリから貼り付けてください。

**⑥ LINE**
- 発行済みの Messaging API の「チャネルアクセストークン（長期）」→ `LINE_CHANNEL_ACCESS_TOKEN`

**⑦ トークン自動更新用（推奨）**
- GitHub → Settings → Developer settings → Fine-grained token を作成
  （対象リポジトリ `crea-auto`、権限 **Secrets: Read and write**）→ `GH_PAT`

### 3. 鍵を GitHub に登録する
リポジトリの **Settings → Secrets and variables → Actions → New repository secret** で、上の名前と値を1つずつ登録。
まだ取れていない媒体の鍵は登録しなくて大丈夫です（その媒体は原稿メールになります）。

### 4. 動かす
1. リポジトリの **Actions** タブ →「I understand…」を押して有効化
2. **毎週の投稿づくり** → Run workflow（初回は手動で1回）
3. 数分で「来週の投稿○件を予約しました」メールが届けば完了。以降は全部自動です。

---

## ふだんの使い方

- **何もしなくてOK。** 毎週日曜に予約一覧メールが届きます。
- **止めたい投稿がある**：GitHub の `data/queue/week-日付.json` を開き、その投稿の `"status": "pending"` を `"skip"` に書き換えて保存
- **⚠保留メールが来た**：NG表現が残ったため自動で止めています。文を直し、`"held"` を `"pending"` に変えると次の30分以内に投稿されます
- **頻度・時間を変えたい**：`config.yaml` の `slots` を編集（例：Threadsを週5回に）
- **LINE配信を増やしたい**：`weeks_of_month: [1, 3]` で月2回に（友だち数×回数が200通を超えないように）

## 安全装置
- 効果の断定・最上級・体験談・病名など、あはき・柔整広告ガイドライン／薬機法／景品表示法で問題になりやすい表現を、作成時と投稿直前の2回チェック
- HPB原稿は「鍼・灸・医学・病院・あん摩・マッサージ指圧」などの登録不可ワードも追加チェック
- NGが1つでも残ったら投稿せず保留＋メール
- 1日の投稿は最大6件まで。予約時刻から12時間以上遅れた投稿は出さない
- 料金・割引は書かせない（クーポンは予約ページで確認する形）

## 困ったとき
| メール内容 | 対処 |
|---|---|
| 「〜がありません」 | その鍵がSecretsに未登録。手順2・3を確認 |
| 401 / token expired | トークン切れ。手順2の③④で取り直してSecretsを上書き |
| LINEの残り通数が足りない | 今月は見送り済み。翌月に自動で再開 |
| Instagram画像の取り込みに失敗 | リポジトリが Public になっているか確認 |

## 有料広告について
Instagram広告・Google広告などの有料広告は、SNSの通常投稿よりも、あはき法の広告規制（広告できる事項が法律で限定されている）がはっきり適用される領域です。AIに自由に広告文を作らせて自動出稿するのはリスクが高いため、この仕組みには入れていません。まず無料の投稿で「伸びる型」のデータを貯め、そのうえで法定事項の範囲に絞った有料広告を別途組むのがおすすめです。
