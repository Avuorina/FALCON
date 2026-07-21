# F.A.L.C.O.N.

**F**ully **A**utonomous **L**inguistic **C**omputing **O**perations **N**etwork

Claude を頭脳に使った、自分専用のAIアシスタント。PCのコンソール版に加え、自宅PCで動くWebサーバー版(PWA)を開発中。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 概要

FALCON は、Anthropic の Claude を頭脳として動く、パーソナルAIアシスタントです。
調べ物・メモ・スケジュール・天気確認などの作業を手伝うことを目指しています。

頭脳部分は **[Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview)** を通して Claude Code 上で動作します。
そのため、**Claude のサブスクリプション(Pro / Max など)でログイン認証すれば、API従量課金なしで利用できます**（APIキーでの従量課金も選択可）。

> **現状**: PC単体で動くコンソール版に加え、自宅PC上でFastAPIサーバーとして動かし、同じWi-Fi内のスマホからPWA(Webアプリ)として利用できるMVPが完成。会話履歴を保持したマルチターン対話、メモの検索・読み出し、Googleカレンダーの閲覧・予定作成、タスクの追加・一覧・完了・削除に対応。
> **最終目標**: サーバー + PWA 構成にして、PCでもスマホでも同じFALCONを使えるようにする。外出先からのアクセス(VPN経由)は今後の課題。

---

## できること

| 機能 | 説明 |
| --- | --- |
| 対話 | 会話の文脈を保持。「じゃあ明日は?」のような前を受けた指示が通る |
| 天気 | 気象庁APIから実データを取得(`get_weather`) |
| メモ | markdownで保存。要約(`summary`)/原文(`raw`)を切替(`save_memo`)。過去のメモは検索・読み出し可能(`list_memos` / `search_memos` / `read_memo`) |
| スケジュール | Googleカレンダーの予定を取得(`list_events`)・作成(`create_event`) |
| タスク | 追加(`add_task`)・一覧(`list_tasks`)・完了(`complete_task`)・削除(`delete_task`)。期限は任意、ローカルのJSONファイルで管理 |
| PWA(スマホ対応) | 自宅PCでサーバー(`server.py`)を起動すれば、同じWi-Fi内のスマホからブラウザ経由で会話できる。ホーム画面に追加してアプリのように使用可能 |

---

## 必要なもの

| 項目 | 要件 |
| --- | --- |
| Python | 3.10 以上 |
| Node.js | 18 以上（Claude Code CLI が必要とする） |
| Claude Code CLI | `@anthropic-ai/claude-code` |
| 認証 | Claude サブスク（Pro/Max等）でのログイン **または** Anthropic APIキー |
| Google Cloud プロジェクト | Calendar連携を使う場合、OAuthクライアント情報(デスクトップアプリ)が必要 |
| (PWA版のみ) 同一Wi-Fiネットワーク | スマホからアクセスする場合、サーバーを動かすPCとスマホが同じWi-Fiに接続している必要がある |

---

## セットアップ

### 1. リポジトリを取得

```bash
git clone https://github.com/Avuorina/FALCON.git
cd FALCON
```

### 2. Claude Code CLI をインストール

```bash
npm install -g @anthropic-ai/claude-code
```

### 3. 仮想環境を作成し、Python の依存をインストール

プロジェクト専用の仮想環境(venv)を作ってから依存を入れることを推奨します。グローバル環境に直接入れると、他のPythonプロジェクトとライブラリのバージョンが衝突するおそれがあります。

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

python -m pip install -r requirements.txt
```

> 有効化に成功すると、ターミナルのプロンプトの先頭に `(.venv)` と表示されます。以降の作業は、この表示がある状態のターミナルで行ってください。迷ったら `python -c "import sys; print(sys.executable)"` で、今どの環境を見ているか確認できます。

### 4. 認証(どちらか一方)

FALCON は自分自身の Claude 認証情報で動きます。以下のどちらかを選んでください。

**A. サブスクリプションで動かす(追加課金なし・推奨)**

Claude Pro / Max 等のサブスク契約がある場合:

```bash
claude        # 起動
/login        # 中で実行し、サブスクアカウントでログイン
/exit
```

> この方法では、利用はサブスクの利用枠から消費されます(API残高は減りません)。
> なお `ANTHROPIC_API_KEY` が環境変数にセットされているとそちらが優先されるため、
> サブスクで動かしたい場合はキーを設定しないでください。

**B. APIキーで動かす(従量課金)**

[Anthropic Console](https://platform.claude.com/) でAPIキーを発行し、環境変数に設定:

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-xxxxx"

# macOS / Linux
export ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 5. Googleカレンダー連携の設定(任意)

スケジュール機能を使う場合、Google Cloud Consoleでの事前設定が必要です。

1. [Google Cloud Console](https://console.cloud.google.com/) で新しいプロジェクトを作成
2. 「APIとサービス」→「ライブラリ」から **Google Calendar API** を有効化
3. 「APIとサービス」→「OAuth同意画面」で、User Typeを「外部」に設定。アプリ名・サポートメールを入力し、テストユーザーに自分のGoogleアカウントを追加
4. 「APIとサービス」→「認証情報」から、種類「デスクトップアプリ」でOAuthクライアントIDを作成し、JSONをダウンロード
5. ダウンロードしたファイルを `config/google_client_secret.json` として配置

初回起動時、Calendar機能を使うタイミングでブラウザが自動的に開き、Googleアカウントでのログイン・許可を求められます。許可すると `config/google_token.json` が自動生成され、以降はブラウザを開かずに利用できます(トークンが期限切れの場合も自動更新されます)。

> `google_client_secret.json` と `google_token.json` はどちらも機密情報です。`.gitignore` に含まれているため、通常はGit管理下に入りません。

### 6. サーバー版(PWA)を使う場合(任意)

スマホからFALCONに話しかけたい場合、自宅PCでサーバーを起動します。

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

- `--host 0.0.0.0` を指定することで、同じWi-Fi内の他の端末(スマホ)からもアクセスできるようになります(`127.0.0.1`のままだと自分自身のPCからしかアクセスできません)。
- サーバーを起動したPCの、Wi-FiのローカルIPアドレス(`ipconfig`や`ifconfig`で確認できる`192.168.x.x`形式のアドレス)を控えておいてください。

スマホのブラウザで `http://(控えたIPアドレス):8000/` を開くとチャット画面が表示されます。共有ボタンから「ホーム画面に追加」すると、アプリのように起動できます。

> サーバーが動いているPCがスリープすると、FALCONも一緒に停止します。スマホから使いたい間は、PCの電源設定で**スリープを無効化**しておいてください(ディスプレイの電源を切るだけなら影響ありません)。

---

## 使い方

**頭脳の動作確認:**

```bash
python core/brain.py
```

会話が繋がっているか(マルチターン)のテストが走ります。

**会話ループ(対話モード)を起動:**

```bash
python main.py
```

`終了` と入力すると停止します。

```
FALCON起動しました。「終了」と入力すると終わります。
隼: 名古屋の天気は?
FALCON: 名古屋(愛知県西部)の天気です。
- 本日17日: 晴れ。夜はくもりで、所により夜のはじめ頃まで雷を伴った激しい雨。
- 明日18日: くもり、朝から昼前にかけて雨。
今夜出かける予定があるなら、傘は持って行くべきですね。
隼: じゃあ明日は?
FALCON: 明日18日はくもり、朝から昼前にかけて雨です。傘をお持ちください。
隼: 今週の予定を教えて
FALCON: 今週の予定です。
- 7/23(木) 18:30〜 会社説明会
- 7/25(土) 体験入学
23日は説明会が夕方からですので、日中の予定は入れられます。
隼: レポート提出をタスクに追加して。期限は7月25日
FALCON: 「レポート提出」を7月25日期限でタスクに追加しました。
隼: タスク一覧見せて
FALCON: 現在のタスクは以下の1件です。
- レポート提出(期限: 7月25日)
```

**サーバー版(PWA)を起動する:**

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

起動後、同じWi-Fi内のスマホのブラウザで`http://(サーバーPCのIPアドレス):8000/`を開くと、チャット画面が表示されます。会話の文脈・履歴はサーバー側で保持されるため、ページをリロードしても会話は消えません。

---

## プロジェクト構成

```
FALCON/
├── .venv/                  # 仮想環境(実行時に作成 / Git管理外)
├── config/
│   ├── google_client_secret.json  # Google OAuthクライアント情報(要作成 / Git管理外)
│   └── google_token.json          # 認証済みトークン(自動生成 / Git管理外)
├── core/
│   ├── brain.py            # 頭脳。Claude Agent SDK 経由でClaudeに問い合わせる
│   └── tools/
│       ├── weather.py      # 気象庁APIから天気予報を取得
│       ├── area_codes.json # 地名 → 気象庁の地域コード対応表
│       ├── memo.py         # メモの保存・一覧・検索・読み出し
│       ├── google_auth.py  # Google OAuth2認証(Calendar共通の認証窓口)
│       ├── calendar.py     # Googleカレンダーの予定取得・作成
│       └── tasks.py        # タスクの追加・一覧・完了・削除
├── memos/                  # メモの保存先(実行時に自動生成 / Git管理外)
├── tasks/                  # タスクの保存先(tasks.json、実行時に自動生成 / Git管理外)
├── static/                 # PWA用の静的ファイル
│   ├── index.html          # チャット画面(HTML/CSS/JS)
│   └── manifest.json       # PWA設定
├── Handover/               # 開発の引継ぎメモ
├── main.py                 # 会話ループ(コンソール版のエントリポイント)
├── server.py                # サーバー版のエントリポイント(FastAPI)
├── requirements.txt
├── .env.example
├── LICENSE                 # MIT
└── README.md
```

---

## 設計メモ

### 会話履歴の保持

`ClaudeSDKClient` を `main.py` 側で1つ生成し、会話ループ全体で使い回すことでセッションを維持しています。
`async with` を `while` ループの**外**に置くことが条件です。中に入れると1ターンごとに再接続され、文脈が失われます。

### ツールの制限

FALCON が使えるツールは、自作のツールのみに限定しています。

```python
tools=[]                # 組み込みツール(Read/Bash/Write等)を全て無効化
strict_mcp_config=True  # 渡したMCPサーバー以外(CLI側の設定)を読み込まない
```

Claude Code CLI は既定で多数の組み込みツールを持ち、さらにログイン中のアカウントに紐づく
外部コネクタも読み込みます。FALCON はそれらを必要としないため、明示的に遮断しています。
必要なツールは `allowed_tools` に1つずつ明示して開放する方針(現在: 天気1・メモ4・カレンダー2・タスク4の計11個)で運用しています。

> `allowed_tools` は「利用可能なツールの制限」ではなく「**確認なしで自動許可するツール**」の指定です。
> 制限には `tools` を使います。

### 現在日時の扱い

Claudeは会話の中で「今日の日付」を自力で正確に把握できるとは限らないため、`ask_claude`関数がユーザーメッセージを送る際に、実行しているPCの現在日時を毎回明示的に付加しています。これにより、Calendarへの予定作成などで日付がズレるリスクを防いでいます。

### Googleカレンダー連携の認証方式

現在のOAuthクライアントは「デスクトップアプリ」種別で作成しており、PC上で直接ブラウザを開いて認証する方式です。将来サーバー+PWA構成に移行する際は、認証をサーバー側に一元化するため、クライアント種別を「ウェブアプリケーション」に作り直す想定です。

### サーバー版のセッション設計

`server.py`では、サーバー起動時に`ClaudeSDKClient`を1回だけ生成し、以降すべてのリクエストで使い回しています(FastAPIの`lifespan`機能を利用)。コンソール版で「`async with`を`while`ループの外に置く」としていた原則を、サーバーの生存期間全体に拡張した形です。リクエストごとにクライアントを作り直すと、会話の文脈が失われてしまいます。

会話履歴(`chat_history`)もサーバー側のメモリ上で一元管理しており、スマホ・PCどちらからアクセスしても同じ履歴が見えます。ただし現状はメモリ上のみの保持のため、**サーバーを再起動すると会話の文脈・履歴の両方がリセットされます**。

---

## ロードマップ

- [x] Claude を頭脳にした最小構成
- [x] Claude Agent SDK への移行(サブスク認証対応)
- [x] 天気取得ツールをFALCONに接続(ツール使用対応)
- [x] ドキュメント・メモの自動生成ツール
- [x] 会話履歴の保持(マルチターン化)
- [x] メモの読み出し(`read_memo` / 長期記憶化)
- [x] Googleカレンダー連携(予定の閲覧・作成)
- [x] タスク管理(ローカル完結の自作。Asanaは有料プランのみだったため見送り)
- [x] サーバー + PWA 化(MVP: 自宅Wi-Fi内でスマホから利用可能)
- [ ] 外出先からのアクセス(VPN経由)・Wake-on-LAN
- [ ] オフライン対応(Service Worker)

---

## ライセンス

[MIT License](LICENSE)