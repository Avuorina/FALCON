# FALCON 開発進捗まとめ(2026/07/25 その3 スマートメモリ)

前回(`0725_DiscordBot.md`)の続き。
Discord Bot化を「コード完成・実機確認待ち」で寝かせたあと、最優先要望のスマートメモリに着手して完成させた回。
この機能は追加ライブラリがゼロ(全て標準ライブラリ)なので、学校ネットでも試せる。
次回はこのファイルの「次回の起点」から始める。

---

## 今日の到達点

- スマートメモリ(3層記憶)を実装完了。構文チェックと実データ非依存の単体テストまで通過。
- **保存はJSON構造化、保存時は黙って行う、プロジェクトは話題から自動判定** の3方針を隼と決めて実装。
- 会話中にFALCONが持続的な事実だけを`remember`で記憶し、毎ターン関連する記憶を文脈へ自動注入する「覚える+思い出す」の両輪が回るようになった。
- 新規1ファイル(`core/tools/memory.py`)、改修2ファイル(`core/brain.py` / `core/session.py`)。全て`py_compile`通過。
- **重要な残作業**: `memory/`を`.gitignore`に追加すること(下記5)。公開リポジトリに個人的な記憶を載せないため。

---

## 1. 決めた方針

- 保存形式はJSON(構造化)。重複整理・更新・種別分けが楽で、`{内容, 種別, プロジェクト, 日時}`を持つ。
- 自動保存時は黙って保存(「覚えました」を返事に付けない)。会話を邪魔せず、記憶の中身はファイルで確認できる。
- プロジェクト記憶の切り替えは話題から自動判定。発言にプロジェクトの表示名が出たら、その記憶を注入する。

## 2. 3層記憶の設計と現状の対応

- 短期記憶(`tier="short"`) … 今回の会話用。`memory/short_term.json`に保存し、`FalconSession.start()`で消す。サーバーが1個のセッションを起動してから再起動するまでが「今回の会話」に当たる。
- 長期記憶(`tier="long"`) … 隼について長く役立つ一般的な事実。`memory/long_term.json`。毎ターン常に文脈へ注入。
- プロジェクト記憶(`tier="project"`) … 特定プロジェクト固有の事実。`memory/projects/<slug>.json`。話題に名前が出たときだけ注入。

注入の実体は`build_context_block()`。短期→長期→プロジェクトの順で`[記憶]`ブロックを組み、メッセージ先頭に差し込む。
記憶は貯めるだけでなく戻して初めて効くため、ここが機能の心臓。

## 3. 実装した内容(ファイルごと)

### 新規 `core/tools/memory.py`(追加依存なし、標準ライブラリのみ)
- `remember(text, tier, project)` … 事実を1件保存。同じ`text`があれば`updated_at`だけ更新(重複防止)。`tier="project"`は`project`必須。
- `recall(keyword, project)` … 空白区切りAND検索で記憶を取り出す。
- `forget(fact_id)` … id指定で1件削除。短期・長期・全プロジェクトを走査。取り消せない。
- `list_projects()` … 記憶を持つプロジェクトの表示名一覧。
- `clear_short_term()` … 短期記憶ファイルを消す。
- `build_context_block(user_message)` … 毎ターン注入する`[記憶]`ブロックを組む。プロジェクトは`user_message`への表示名一致で選ぶ。
- `_slugify()` … プロジェクト名をファイル名に無害化(`memo.py`流)。`\w`とハイフン以外を`_`に潰し、`../`等で`projects/`の外を指せないようにしている。

### 改修 `core/brain.py`
- import追加(`from core.tools.memory import remember, recall, forget, build_context_block`)。
- `ask_claude`に自動注入を1行追加。日付の前に`build_context_block(user_message)`を差し込む。
- `remember` / `recall` / `forget`を`@tool`登録し、`create_sdk_mcp_server`のツール一覧と`allowed_tools`の両方に追加。
- `SYSTEM_PROMPT`に「スマートメモリ」節を追記。3層の定義、覚える基準、黙って保存、プロジェクトは話題から判定、`[記憶]`に既出の事実は再保存しない(重複防止)、`forget`は確認、を明記。

### 改修 `core/session.py`
- `start()`の先頭で`clear_short_term()`を呼ぶ。前回会話の短期記憶を持ち越さない。
- (この`session.py`は`0725_DiscordBot.md`で新設したもの。今回さらに短期クリアの1行を足した版。)

## 4. 動作確認(このセッションで実施)

- `py_compile`: `memory.py` / `session.py` / `brain.py` すべて通過。
- 単体テスト(保存先を一時ディレクトリに差し替え、実データ非汚染):
  - 長期・プロジェクト・短期の保存、同一内容の重複防止(2回目は`updated=True`)を確認。
  - `build_context_block`が、話題に`ExcelDestroyer`が出たときだけ該当プロジェクト記憶を注入し、短期→長期→プロジェクトの順で並ぶことを確認。
  - `clear_short_term()`後に短期記憶だけ消えることを確認。
  - `_slugify`が`../../../etc/passwd`を`projects/`内に閉じ込めることを確認。
- 実会話での確認は自宅/学校いずれでも可(追加依存なし)。手順は「Mayaをよく使う」と言う→別の話→「よく使うツールは?」で長期記憶から答えられるか。`memory/long_term.json`で保存内容も目視できる。

## 5. 次回の起点(優先順)

**1. `memory/`を`.gitignore`に追加(最優先、コミット前に必須)**
FALCONリポジトリはPublic(MIT)。`memory/`を除外しないと個人的な記憶が公開される。
既存の`memos/`(`.gitignore`の225行目)と同じ扱いにする。`.gitignore`に次を追加:
```
# memory
memory/
```
これを入れてから`git add`する。先にコミットすると公開履歴に残るので順番厳守。

**2. コンソール版`main.py`の短期記憶クリア(任意)**
`main.py`は`FalconSession`を使わず`ask_claude`を直に呼ぶため、起動時の`clear_short_term()`が走らない。
コンソールを使うと前回の短期記憶が残る場合がある。気になれば`main.py`にも`clear_short_term()`を1行足す。

**3. プロジェクト自動判定の格上げ(将来)**
現状は「表示名が発言に文字列一致するか」の素朴な判定。「あれの続き」等、名前を出さない言い方は拾えない。
FALCON自身が話題からプロジェクトを判断して`recall(project=...)`を呼ぶツール方式へ格上げできる。トレードオフは1往復増えること。

**4. Discord通知トリガー(持ち越し)**
`0725_DiscordBot.md`のステップ7。`bot.notify()`は用意済み。記憶と組み合わせ、朝のまとめに長期記憶を反映する等も将来可能。

## 6. コミット(gitmoji)案

- ✨ スマートメモリ`core/tools/memory.py`を追加(3層記憶: 短期/長期/プロジェクト、JSON保存)
- ✨ `brain.py`に記憶ツール(remember/recall/forget)を登録し、毎ターンの記憶自動注入を追加
- ✨ `SYSTEM_PROMPT`に記憶運用ルールを追記(黙って保存、話題からプロジェクト判定、重複防止)
- ♻️ `FalconSession.start()`で短期記憶をクリア(今回の会話の起点)
- 🙈 `.gitignore`に`memory/`を追加(個人的な記憶を公開リポジトリから除外)
- 📝 引継書追加(0725その3、スマートメモリの設計と実装の記録)