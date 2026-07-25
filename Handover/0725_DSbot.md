# FALCON 開発進捗まとめ(2026/07/25 その2 Discord Bot化)

前回(`0725.md`)の続き。
Minecraftツールの`brain.py`登録は今回も保留のまま、持ち越し課題だったDiscord Bot化に着手した回。
設計とコードは一式そろったが、実行確認(Discordトークン取得・`pip install`・`python run.py`)は自宅ネットに持ち帰る。
次回はこのファイルの「次回の起点」から始める。

---

## 今日の到達点

- Discord Bot化のコード一式が完成(構文チェックのみ通過、実機確認は未)。DM専用・隼本人限定・通知対応の設計。
- **セッション共有の設計を確定** … `ClaudeSDKClient`の「同一イベントループ制約」を実物のソースで確認し、サーバー(PWA)とDiscordを同一プロセスで動かして1個のセッションを共有する形にした。
- **利用規約を確認して方針転換** … サブスクログインのまま他人に使わせるのは規約違反と判明。DM専用+本人限定の「個人利用」に切り替えて回避した。
- **役割を「反応する窓口」から「通知を出す口」へ** … 反応するだけならPWAと機能が被るため、FALCON側から隼のDMに通知を送る機能を主役に据えた。
- 新規3ファイル(`core/session.py` / `discord_bot.py` / `run.py`)、既存3ファイル改修(`server.py` / `.env.example` / `requirements.txt`)。全ファイル`py_compile`通過。

---

## 1. セッション共有の設計(SDK制約の発見)

「コンソール・サーバー・Discordで1つの記憶を共有したい」が出発点。
`ClaudeSDKClient`のソース(`src/claude_agent_sdk/client.py`)を直接読んで、次の2点を確認した。

- `async with`だけでなく、`await client.connect()` / `await client.disconnect()`で手動でも寿命管理できる。よって「1個作って持ち回る」形は作れる。
- ただし重要な制約がある。原文は "you cannot use a ClaudeSDKClient instance across different async runtime contexts ... you must complete all operations with the client within the same async context where it was connected"。
  クライアントは接続時に「返事を読み続ける常駐タスク」を立ち上げるため、接続したのと同じイベントループの中でしか使えない。

この制約から、現実的に一枚岩で共有できるのはサーバー(PWA)とDiscordの2つと結論した。
コンソール(`main.py`)は`input()`で動く独立プロセスで別イベントループになるため、動いているサーバーとメモリ共有できない。
コンソールも同じ記憶に混ぜたい場合は、コンソールを自前クライアントからHTTP経由(ダッシュボードと同じ方式)に作り替える必要がある。これは将来の課題として保留。

もう1点、1個のクライアントは一度に1つの会話ストリームしか捌けない。
PWAとDiscordが同時に叩くと読み取りが混線しうるため、共有側に`asyncio.Lock`を仕込んで1件ずつ直列化した。

## 2. 利用規約の確認と方針転換

当初は「サーバーでメンションされたら反応(みんなが使える)」を想定していたが、規約を確認して取りやめた。
引っかかる点は2つ。

- アカウント共有の禁止。消費者向け規約は、ログイン情報や認証情報を他人と共有すること、アカウントを他人が使えるようにすることを禁じている。
- 2026年2月にAnthropicが明文化した規定。Free/Pro/MaxのサブスクOAuth認証を、Claude CodeとClaude.ai以外の第三者向けプロダクト・ツール・サービスに使うことを禁止。Agent SDK開発ではConsole発行のAPIキー認証を使うよう求めている。

FALCONはAgent SDK製でサブスクログイン運用のため、他人に開放した瞬間ここに抵触する。
選択肢は「個人利用のまま(隼専用)」か「APIキー従量課金に切り替えて共有OK」の2つ。
今回は追加課金なしで規約もクリアな前者を選んだ。

重要な帰結として、隼一人だけの専用サーバーであれば第三者利用に当たらず問題ない。
保険として、Botアプリは非公開(他人が招待できない)にし、コード側でも発言者を隼のユーザーIDに限定した。

参考(次回の判断用):
- https://alternativeto.net/news/2026/2/anthropic-officially-bans-using-subscription-authentication-for-third-party-claude-use
- https://www.theregister.com/software/2026/02/20/anthropic-clarifies-ban-on-third-party-tool-access-to-claude/5014546
- https://anthropic.com/legal/terms

## 3. 「通知」を主役にした理由

DM専用+本人限定にすると、Botは「隼が質問して答える」窓口になり、Tailscale経由で使えるPWAと用途が被る。
被らない価値は「FALCON側から通知を飛ばせる」点にしかない。
PWAは隼が開かないと喋れないが、Discordは常駐アプリで通知が鳴るため、アラーム時刻・タスク期限・朝のまとめを向こうから届けられる。
この能動通知を実装の主目的に据えた。

---

## 4. 成果物(ファイルごとの役割)

### 新規 `core/session.py`
`FalconSession`クラス。`ClaudeSDKClient`を1個だけ抱え、複数の入り口で共有するための器。
- `start()` / `stop()` … 接続と切断。プロセス起動・停止時に1回ずつ。
- `ask(sender, message)` … 1往復の会話。`asyncio.Lock`で囲って混線を防ぎ、履歴追記もこの中でやる。
- `history` … PWAとDiscordで共有する会話ログ。以前`server.py`にあった`chat_history`をここへ移した。
- 頭脳のロジックは`brain.py`の`ask_claude`をそのまま呼ぶ。器で包んだだけで、頭脳は書き換えていない。

### 改修 `server.py`
グローバルの`falcon_client` + `chat_history`を、`FalconSession`1個(`session`)に置き換えた。
- `lifespan`は`session.start()` / `session.stop()`の2行に。
- `/chat`は`session.ask("隼", ...)`の1行に。
- `/history`は`session.history`を返す。
- 挙動変更が1点。起動前の`falcon_client is None`ガードを外した(FastAPIは`lifespan`完了までリクエストを捌かないため通常は不要)。`start()`が失敗した場合は500になる。

### 新規 `discord_bot.py`(リポジトリ直下)
`FalconBot(discord.Client)`。隼専用DM Bot。
- インテントは`message_content = True`(特権インテント。Developer Portal側でも有効化が必須)。
- `on_message`の3段フィルタ。Bot自身→無視(無限ループ防止)、隼以外→無視(規約・事故防止)、DM以外→無視。
- `notify(text)` … FALCON側から隼のDMに送る通知の共通入口。Botと隼が同じサーバーに同居している前提。
- `_send_long` … Discordの1メッセージ2000字上限に対応し、長文を分割送信する。

### 新規 `run.py`(リポジトリ直下、今後の起動口)
`uvicorn`と`discord`を1つのイベントループで同時起動する入口。
- `from server import app, session`で、サーバーと同じ`session`をBotに渡す。これが記憶共有の実体。
- `asyncio.gather(server.serve(), bot.start(token))`で同居させ、SDKの同一ループ制約を満たす。
- `.env`から`DISCORD_TOKEN` / `DISCORD_OWNER_ID`、任意で`SSL_CERTFILE` / `SSL_KEYFILE` / `PORT`を読む。証明書が両方あればHTTPS、無ければHTTP。
- 起動コマンドは今後`python run.py`。以前の`uvicorn server:app ...`は不要になる(SSL引数も`.env`へ移行)。

### 改修 `.env.example` / `requirements.txt`
- `.env.example`に`DISCORD_TOKEN` / `DISCORD_OWNER_ID` / `SSL_CERTFILE` / `SSL_KEYFILE` / `PORT`の枠を追加。
- `requirements.txt`に`discord.py`と`python-dotenv`を追加。
- `.env`は`.gitignore`済み(151行目)、追跡もされていないためトークンは漏れない。

---

## 5. 次回の起点(優先順)

**1. 実機セットアップとDM会話の動作確認**(自宅ネット)
- Discord Developer Portalでアプリ作成→Bot追加→トークン発行。「MESSAGE CONTENT INTENT」をONにする(ここを忘れるとDM本文が読めない)。アプリは非公開のまま。
- OAuth2でscope`bot`の招待URLを生成し、隼専用サーバーにBotを招待。
- Discord開発者モードをONにして自分のユーザーIDをコピー。
- `.env.example`を`.env`にコピーし、トークンとユーザーIDを記入。
- `pip install -r requirements.txt`(学校ネットはpypi不可、自宅で)。
- `python run.py`で起動し、BotにDM→PWAと同じFALCONが返事すれば成功。PWAと会話履歴が共有されることも確認する。

**2. 通知トリガーの実装**(ステップ7、未着手)
- `notify()`は用意済み。あとは「いつ・何を」飛ばすかの条件判定と背景ループ。
- 候補はアラーム時刻・タスク期限・朝のまとめ。どれを優先するかは未決定、次回まず決める。
- 設計案は`discord.ext.tasks`の定期ループ(例: 1分ごとに条件チェック)か、既存の`schedule`系スケジューラ連携。同一プロセスなので`session`や`tasks.json`を直接読める。
- 通知はすべて`bot.notify()`を通す。Botの参照をスケジューラ側に渡す配線が必要。

**3. 起動順の小さな注意**(必要なら)
- `bot.start()`と`session.start()`がほぼ同時に走るため、理屈上は`session`起動前のDMで「未起動」エラーになりうる。現実にはまず起きないが、気になれば「session起動後に受付開始」の順序付けを足す。

**4. コンソールのHTTP化**(将来)
- コンソールも記憶を完全共有したい場合、`main.py`を自前クライアントからサーバーへのHTTPクライアントに作り替える。トレードオフはサーバー必須になること。

---

## 6. コミット(gitmoji)案

- ✨ 共通セッションモジュール`core/session.py`を追加(FalconSession、接続管理・共有履歴・Lockによる直列化)
- ♻️ `server.py`をFalconSession共有に置き換え(falcon_client/chat_historyを集約)
- ✨ Discord Bot`discord_bot.py`を追加(DM専用・隼本人限定・notifyによる能動通知)
- ✨ サーバーとDiscordを同一プロセスで起動する`run.py`を追加
- 🔧 `.env.example`にDiscord/SSL設定を追加、`requirements.txt`に`discord.py`・`python-dotenv`を追加
- 📝 引継書追加(0725その2、Discord Bot化の設計と規約判断の記録)