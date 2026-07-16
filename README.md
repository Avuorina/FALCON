# F.A.L.C.O.N.

**F**ully **A**utonomous **L**inguistic **C**omputing **O**perations **N**etwork

Claude を頭脳に使った、自分専用のAIアシスタント。まずはPCのコンソールで動く版を開発中。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 概要

FALCON は、Anthropic の Claude を頭脳として動く、パーソナルAIアシスタントです。
調べ物・メモ・スケジュール・天気確認などの作業を手伝うことを目指しています。

頭脳部分は **[Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview)** を通して Claude Code 上で動作します。
そのため、**Claude のサブスクリプション(Pro / Max など)でログイン認証すれば、API従量課金なしで利用できます**（APIキーでの従量課金も選択可）。

> **現状**: PC単体で動くコンソール版。
> **最終目標**: サーバー + PWA 構成にして、PCでもスマホでも同じFALCONを使えるようにする。

---

## 必要なもの

| 項目 | 要件 |
| --- | --- |
| Python | 3.10 以上 |
| Node.js | 18 以上（Claude Code CLI が必要とする） |
| Claude Code CLI | `@anthropic-ai/claude-code` |
| 認証 | Claude サブスク（Pro/Max等）でのログイン **または** Anthropic APIキー |

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

### 3. Python の依存をインストール

```bash
python -m pip install -r requirements.txt
```

### 4. 認証（どちらか一方）

FALCON は自分自身の Claude 認証情報で動きます。以下のどちらかを選んでください。

**A. サブスクリプションで動かす（追加課金なし・推奨）**

Claude Pro / Max 等のサブスク契約がある場合:

```bash
claude        # 起動
/login        # 中で実行し、サブスクアカウントでログイン
/exit
```

> この方法では、利用はサブスクの利用枠から消費されます（API残高は減りません）。
> なお `ANTHROPIC_API_KEY` が環境変数にセットされているとそちらが優先されるため、
> サブスクで動かしたい場合はキーを設定しないでください。

**B. APIキーで動かす（従量課金）**

[Anthropic Console](https://platform.claude.com/) でAPIキーを発行し、環境変数に設定:

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-xxxxx"

# macOS / Linux
export ANTHROPIC_API_KEY=sk-ant-xxxxx
```

---

## 使い方

**頭脳の動作確認:**

```bash
python core/brain.py
```

**会話ループ（対話モード）を起動:**

```bash
python main.py
```

`終了` と入力すると停止します。

```
FALCON起動しました。「終了」と入力すると終わります。
隼: こんにちは
FALCON: こんにちは、隼さん。FALCONです。今日は何をお手伝いしましょうか?
```

---

## プロジェクト構成

```
FALCON/
├── core/
│   ├── brain.py            # 頭脳。Claude Agent SDK 経由でClaudeに問い合わせる
│   └── tools/
│       ├── weather.py      # 気象庁APIから天気予報を取得
│       └── area_codes.json # 地名 → 気象庁の地域コード対応表
├── main.py                 # 会話ループ(コンソール版のエントリポイント)
├── requirements.txt
├── .env.example
├── LICENSE                 # MIT
└── README.md
```

---

## ロードマップ

- [x] Claude を頭脳にした最小構成
- [x] Claude Agent SDK への移行（サブスク認証対応）
- [ ] ドキュメント・メモの自動生成ツール
- [ ] 天気取得ツールをFALCONに接続（ツール使用対応）
- [ ] 会話履歴の保持（マルチターン化）
- [ ] タスク・スケジュール管理
- [ ] サーバー + PWA 化（PC / スマホ両対応）

---

## ライセンス

[MIT License](LICENSE)