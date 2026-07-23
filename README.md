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

> **現状**: PC単体で動くコンソール版に加え、自宅PC上でFastAPIサーバー(HTTPS対応)として動かし、Tailscale経由で外出先からもスマホでPWA(Webアプリ)として利用できる。会話履歴を保持したマルチターン対話、メモの検索・読み出し、Googleカレンダーの閲覧・予定作成、タスクの追加・一覧・完了・削除、PCの電源プラン操作、CPU/メモリ/ネットワーク使用率の表示、音声入力・音声出力(ブラウザ標準機能)、サーバー停止時のオフライン案内表示に対応。
> **最終目標(達成)**: サーバー + PWA 構成にして、PCでもスマホでも同じFALCONを使えるようにする。外出先からのアクセスはTailscaleのVPN経由で実現済み。次のフェーズは新機能追加や既存機能のブラッシュアップ。

---

## できること

| 機能 | 説明 |
| --- | --- |
| 対話 | 会話の文脈を保持。「じゃあ明日は?」のような前を受けた指示が通る |
| 天気 | 気象庁APIから実データを取得(`get_weather`) |
| メモ | markdownで保存。要約(`summary`)/原文(`raw`)を切替(`save_memo`)。過去のメモは検索・読み出し可能(`list_memos` / `search_memos` / `read_memo`) |
| スケジュール | Googleカレンダーの予定を取得(`list_events`)・作成(`create_event`) |
| タスク | 追加(`add_task`)・一覧(`list_tasks`)・完了(`complete_task`)・削除(`delete_task`)。期限は任意、ローカルのJSONファイルで管理 |
| 電源プラン操作 | 「省電力にして」「普段通りに戻して」等の指示でPCの電源プランを切替(`set_power_plan` / `get_power_plan`) |
| PWA(スマホ対応) | 自宅PCでサーバー(`server.py`)を起動すれば、Tailscale経由で外出先からもブラウザ経由で会話できる。ホーム画面に追加してアプリのように使用可能。専用アイコン(仮)対応済み |
| オフライン対応 | サーバーが停止していてもService Workerが案内ページ(`offline.html`)を表示し、真っ白な画面にならない |
| システム状態表示 | ヘッダーにCPU/メモリ/ネットワーク使用率をリアルタイム表示(`psutil`) |
| 音声入出力 | ブラウザ標準のWeb Speech APIでマイク入力・読み上げに対応。声で話しかけた時だけ、返事の後に自動で聞き取りを再開する連続会話モードあり |

---

## 必要なもの

| 項目 | 要件 |
| --- | --- |
| Python | 3.10 以上 |
| Node.js | 18 以上（Claude Code CLI が必要とする） |
| Claude Code CLI | `@anthropic-ai/claude-code` |
| 認証 | Claude サブスク（Pro/Max等）でのログイン **または** Anthropic APIキー |
| Google Cloud プロジェクト | Calendar連携を使う場合、OAuthクライアント情報(デスクトップアプリ)が必要 |
| (PWA版のみ) 同一Wi-Fiネットワーク、または | スマホからアクセスする場合、サーバーを動かすPCとスマホが同じWi-Fiに接続している必要がある |
| Tailscaleアカウント(任意) | 外出先からアクセスしたい場合、および音声入出力(要HTTPS)を使いたい場合に必要。無料枠で利用可能 |

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

> サーバーが動いているPCがスリープすると、FALCONも一緒に停止します。スマホから使いたい間は、PCの電源設定で**スリープを無効化**しておいてください(ディスプレイの電源を切るだけなら影響ありません)。FALCONに「省電力にして」と話しかければ、ディスプレイ消灯等はそのままにスリープだけ無効化した電源プランに切り替えられます。

### 7. 外出先からのアクセス・音声入出力を使う場合(任意・推奨)

上記6のままだと、自宅Wi-Fi内からしかアクセスできず、また音声入力・読み上げ機能は**HTTPS環境でないと動作しません**(ブラウザの仕様上の制約)。[Tailscale](https://tailscale.com/)を導入し、HTTPS証明書機能を有効化することで両方解決します。

1. サーバーを動かすPC・使用するスマホの両方に、同じアカウントでTailscaleをインストール
2. [Tailscale管理画面](https://login.tailscale.com/admin/dns)で「HTTPS Certificates」を有効化
3. PCのフルドメイン名を確認(管理画面の対象デバイス詳細→「Full domain」、`xxxx.yyyy.ts.net`の形式)
4. 証明書を取得:
   ```bash
   tailscale cert <取得したフルドメイン名>
   ```
5. HTTPSでサーバーを起動:
   ```bash
   uvicorn server:app --host 0.0.0.0 --port 8000 --ssl-certfile=<ドメイン名>.crt --ssl-keyfile=<ドメイン名>.key
   ```
6. スマホから `https://<フルドメイン名>:8000/` にアクセス(IPアドレスではなくドメイン名でアクセスすること。証明書がドメイン名向けに発行されているため)

> `.crt` / `.key` は秘密鍵を含む機密情報です。`.gitignore` に含まれているため、通常はGit管理下に入りません。

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
│       ├── gcal.py         # Googleカレンダーの予定取得・作成(標準ライブラリのcalendarと名前が衝突するためgcalに改名)
│       ├── tasks.py        # タスクの追加・一覧・完了・削除
│       ├── power.py        # Windowsの電源プラン切替・取得
│       └── system_stats.py # CPU/メモリ/ネットワーク使用率の取得(psutil)
├── memos/                  # メモの保存先(実行時に自動生成 / Git管理外)
├── tasks/                  # タスクの保存先(tasks.json、実行時に自動生成 / Git管理外)
├── static/                 # PWA用の静的ファイル
│   ├── index.html          # チャット画面(HTML/CSS/JS。音声入出力・Service Worker登録含む)
│   ├── manifest.json       # PWA設定
│   ├── offline.html        # サーバー停止時にService Workerが表示する案内ページ
│   ├── sw.js               # Service Worker本体(オフライン対応)
│   └── icons/              # PWAアイコン一式(仮アイコン、後で差し替え可能)
├── Handover/               # 開発の引継ぎメモ
├── main.py                 # 会話ループ(コンソール版のエントリポイント)
├── server.py                # サーバー版のエントリポイント(FastAPI。/sw.jsの配信も担当)
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
必要なツールは `allowed_tools` に1つずつ明示して開放する方針で運用しています。

> `allowed_tools` は「利用可能なツールの制限」ではなく「**確認なしで自動許可するツール**」の指定です。
> 制限には `tools` を使います。

### 現在日時の扱い

Claudeは会話の中で「今日の日付」を自力で正確に把握できるとは限らないため、`ask_claude`関数がユーザーメッセージを送る際に、実行しているPCの現在日時を毎回明示的に付加しています。これにより、Calendarへの予定作成などで日付がズレるリスクを防いでいます。

### Googleカレンダー連携の認証方式

現在のOAuthクライアントは「デスクトップアプリ」種別で作成しており、PC上で直接ブラウザを開いて認証する方式です。サーバー+PWA構成に移行した後も、認証フローはサーバーを動かすPC自身で完結するため、この方式のままで実害はありません。

「ウェブアプリケーション」種別への変更は、以下のいずれかが実際に発生した場合にのみ検討します(それまでは保留)。

- リフレッシュトークンが数日で失効するようになった場合(この場合はOAuth同意画面の「公開ステータス」を「本番」に切り替えるのが正しい対処であり、クライアント種別の変更とは別の話)
- 外出先からFALCON経由で使用中に、PCの前にいない状態で初回認証をやり直す必要が生じた場合

### サーバー版のセッション設計

`server.py`では、サーバー起動時に`ClaudeSDKClient`を1回だけ生成し、以降すべてのリクエストで使い回しています(FastAPIの`lifespan`機能を利用)。コンソール版で「`async with`を`while`ループの外に置く」としていた原則を、サーバーの生存期間全体に拡張した形です。リクエストごとにクライアントを作り直すと、会話の文脈が失われてしまいます。

会話履歴(`chat_history`)もサーバー側のメモリ上で一元管理しており、スマホ・PCどちらからアクセスしても同じ履歴が見えます。ただし現状はメモリ上のみの保持のため、**サーバーを再起動すると会話の文脈・履歴の両方がリセットされます**。

### HTTPS化とService Worker

外出先からのアクセス(Tailscale経由)と音声入出力機能のために、TailscaleのHTTPS証明書機能でサーバーをHTTPS化しています。これにより、ブラウザの「安全なコンテキスト」制約(HTTPSかlocalhostでしか動かない機能群、Service WorkerやWeb Speech API等)の制約をクリアしています。

Service Worker(`static/sw.js`)は、ページ本体(`/`)へのアクセスを制御下に置く必要があるため、`/static/sw.js`ではなく`server.py`が用意する`/sw.js`エンドポイントから配信しています。`/static/`配下から配信すると、Service Workerが制御できる範囲(scope)がそのディレクトリ配下に限定され、肝心のページ本体を横取りできなくなるためです。

静的ファイル(アイコン・manifest等)を更新した際は、`static/sw.js`内の`CACHE_NAME`のバージョン文字列を必ず変更してください。変更しないと、ブラウザが古いキャッシュを保持し続け、更新が反映されません。

### 音声入出力

音声認識(STT)・音声合成(TTS)ともに、追加のAPIキーや常駐ソフトを必要としないブラウザ標準機能(Web Speech API)で実装しています。対応していないブラウザ(Firefox等)ではマイクボタンが自動的に非表示になり、テキスト入力のみで問題なく利用できます。

音声で話しかけた場合のみ、FALCONの読み上げが完了した後に自動で聞き取りを再開する「連続会話モード」があります。テキストで入力した場合は自動再開しません(意図せずマイクが起動して驚くことを防ぐため)。

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
- [x] 外出先からのアクセス(Tailscale VPN経由)
- [x] TailscaleのHTTPS証明書導入
- [x] オフライン対応(Service Worker)
- [x] PWAアイコン(仮実装。本番画像は準備中)
- [x] UIのJARVIS風ダークテーマへの刷新
- [x] PCの電源プラン操作(`set_power_plan` / `get_power_plan`)
- [x] CPU/メモリ/ネットワーク使用率のリアルタイム表示
- [x] 音声入力・音声出力(Web Speech API)、連続音声会話モード
- [ ] Wake-on-LAN(中継用ハードウェア無しでは実現困難なため保留中)
- [ ] Google OAuthのウェブアプリ種別化(実害無いため保留中。再浮上条件は設計メモ参照)
- [ ] 背景ビジュアル画像の組み込み(準備中の画像を差し込むだけの状態)

---

## ライセンス

[MIT License](LICENSE)