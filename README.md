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

> **現状**: PC単体で動くコンソール版。会話履歴を保持したマルチターン対話に対応。
> **最終目標**: サーバー + PWA 構成にして、PCでもスマホでも同じFALCONを使えるようにする。

---

## できること

| 機能 | 説明 |
| --- | --- |
| 対話 | 会話の文脈を保持。「じゃあ明日は?」のような前を受けた指示が通る |
| 天気 | 気象庁APIから実データを取得(`get_weather`) |
| メモ | markdownで保存。要約(`summary`)/原文(`raw`)を切替(`save_memo`) |

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

会話が繋がっているか（マルチターン）のテストが走ります。

**会話ループ（対話モード）を起動:**

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
```

---

## プロジェクト構成

```
FALCON/
├── core/
│   ├── brain.py            # 頭脳。Claude Agent SDK 経由でClaudeに問い合わせる
│   └── tools/
│       ├── weather.py      # 気象庁APIから天気予報を取得
│       ├── area_codes.json # 地名 → 気象庁の地域コード対応表
│       └── memo.py         # メモをmarkdownとして保存
├── memos/                  # メモの保存先(実行時に自動生成 / Git管理外)
├── Handover/               # 開発の引継ぎメモ
├── main.py                 # 会話ループ(コンソール版のエントリポイント)
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

FALCON が使えるツールは、自作の `get_weather` / `save_memo` の **2つだけ**に限定しています。

```python
tools=[]                # 組み込みツール(Read/Bash/Write等)を全て無効化
strict_mcp_config=True  # 渡したMCPサーバー以外(CLI側の設定)を読み込まない
```

Claude Code CLI は既定で多数の組み込みツールを持ち、さらにログイン中のアカウントに紐づく
外部コネクタも読み込みます。FALCON はそれらを必要としないため、明示的に遮断しています。
副次効果として、コンテキストに載るツール定義が減り、トークン消費と応答時間も大きく改善しています。

> `allowed_tools` は「利用可能なツールの制限」ではなく「**確認なしで自動許可するツール**」の指定です。
> 制限には `tools` を使います。

---

## ロードマップ

- [x] Claude を頭脳にした最小構成
- [x] Claude Agent SDK への移行（サブスク認証対応）
- [x] 天気取得ツールをFALCONに接続（ツール使用対応）
- [x] ドキュメント・メモの自動生成ツール
- [x] 会話履歴の保持（マルチターン化）
- [ ] メモの読み出し（`read_memo` / 長期記憶化）
- [ ] タスク・スケジュール管理
- [ ] サーバー + PWA 化（PC / スマホ両対応）

---

## ライセンス

[MIT License](LICENSE)