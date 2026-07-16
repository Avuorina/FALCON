# FALCON ノートPC セットアップ手順

別マシン(ノートPC)でFALCONを動かすための、インストールするモジュールと実行コマンド一覧。
上から順に実行すればOK。

> **注意(学校ネットワーク)**: 学校のネットは pypi.org / npm への通信がブロックされることがある。
> `pip install` や `npm install` は**自宅ネットワークで**済ませておくこと。

---

## インストールするもの一覧

| # | 種類 | 名前 | 用途 |
| --- | --- | --- | --- |
| 1 | ランタイム | Python 3.10 以上 | FALCON本体 |
| 2 | ランタイム | Node.js 18 以上 | Claude Code CLI の土台 |
| 3 | グローバルCLI | `@anthropic-ai/claude-code` | FALCONの頭脳が経由する本体(npm) |
| 4 | Pythonモジュール | `claude-agent-sdk` | PythonからClaude Codeを呼ぶ |
| 5 | Pythonモジュール | `requests` | 天気ツールが気象庁APIを叩く |

(4・5 は `requirements.txt` にまとめてあるので一括インストール可)

---

## 手順

### 1. Python / Node.js の確認

```powershell
python --version    # 3.10 以上ならOK
node --version      # 18 以上ならOK
npm --version
```

- 入ってなければ: Python → https://www.python.org / Node.js(LTS) → https://nodejs.org
- インストール後は PowerShell を開き直すこと

### 2. PowerShell 実行ポリシーの解除(初回のみ)

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

- `npm` や `claude` が「スクリプト実行が無効」で弾かれるのを防ぐ
- 途中で聞かれたら `Y` → Enter。管理者権限は不要

### 3. Claude Code CLI をインストール

```powershell
npm install -g @anthropic-ai/claude-code
claude --version
```

- バージョンが出ればOK

### 4. Claude サブスクでログイン(このマシンでも必要)

```powershell
claude          # 起動
/login          # 中で実行 → サブスク(Pro/Max)アカウントでログイン
/exit
```

- 認証情報はマシンごとに保存されるので、ノートPCでも1回はログインが必要
- `ANTHROPIC_API_KEY` を環境変数にセットしないこと(セットするとAPI課金が優先される)

### 5. リポジトリを取得

```powershell
git clone https://github.com/Avuorina/FALCON.git
cd FALCON
```

(すでにクローン済みなら `cd FALCON` して `git pull`)

### 6. Python モジュールをインストール

```powershell
python -m pip install -r requirements.txt
```

- `claude-agent-sdk` と `requests` が入る
- 個別に入れるなら: `python -m pip install claude-agent-sdk requests`

### 7. 動作確認

```powershell
python core\brain.py     # 頭脳の単体テスト(挨拶が返ればOK)
python main.py           # 会話モード(「終了」で抜ける)
```

---

## よくあるエラーと対処

| 症状 | 原因 | 対処 |
| --- | --- | --- |
| `pip`/`npm` がタイムアウト | 学校ネットのブロック | 自宅ネットで実行 |
| `npm : スクリプトの実行が無効` | 実行ポリシー未設定 | 手順2を実行 |
| `command not found: claude` | CLI未インストール/PATH未反映 | 手順3、PowerShell開き直し |
| 認証エラー | ログイン未実施 or APIキーが環境変数に残存 | 手順4、`echo $env:ANTHROPIC_API_KEY` が空か確認 |
| 天気が404 | area_codes.json が旧コード | `230000`(愛知)/`220000`(静岡)に修正 |

---

## メモ

- `.env` は使わない(サブスク認証に移行済み)。APIキー方式で動かす場合のみ `.env` か環境変数にキーを設定
- 今後モジュールを追加したら `requirements.txt` に1行足して、このファイルの一覧も更新すること