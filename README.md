# git-work-summary-skill

Gitのコミット履歴と差分を確認し、`natural-japanese` で読みやすい日本語の作業報告にまとめる、Codex・Claude Code向けのスキルです。依頼があれば、未コミットの変更を翌日の予定として整理します。

## 必要なもの

- Codex・Claude Codeなど、`SKILL.md` 形式のスキルを利用できるエージェント
- Git 2.37以降、Python 3.10以降
- **別途導入した [natural-japanese](https://github.com/coji/natural-japanese) スキル**。このリポジトリには同梱していません。提供元のREADMEに従って導入してください。
- natural-japaneseのlintには、その版が指定する依存パッケージと実行環境。PEP 723形式の依存宣言がある版では `uv run` を利用できます。使えない場合は同スキルの手動チェックリストで確認します。

Gitの履歴収集スクリプトにはPython標準ライブラリ以外の依存はありません。Windows・macOS・Linuxで使える構成です。動作確認はWindowsで行っています。

## 導入

このリポジトリをcloneまたはダウンロードして、`skills/git-work-summary` フォルダを、利用するエージェントの探索先にコピーします。ReleaseのZIPを使う場合は、展開した `git-work-summary` フォルダをそのまま配置します。

| エージェント | 用途 | コピー先 |
| --- | --- | --- |
| Codex | 自分の環境で使う | `~/.agents/skills/git-work-summary/` |
| Codex | プロジェクトで共有する | `<project>/.agents/skills/git-work-summary/` |
| Claude Code | 自分の環境で使う | `~/.claude/skills/git-work-summary/` |
| Claude Code | プロジェクトで共有する | `<project>/.claude/skills/git-work-summary/` |

Claude Codeの配置先は、[公式のスキル仕様](https://code.claude.com/docs/en/skills#choose-where-skills-load) に沿っています。

`~` は利用者自身のホームフォルダです。`CODEX_HOME`を使う環境では、その環境が指定するスキルの探索先に配置してください。`natural-japanese` も、同じエージェントから見つかる探索先に配置します。このリポジトリ直下をcloneしただけでは、スキルが自動で登録されるとは限りません。導入後は新しいセッションで呼び出します。

natural-japaneseは、提供元が案内する次のコマンドで導入できます。画面の案内に従い、利用するエージェントとインストール先を選んでください。

```text
npx skills add coji/natural-japanese
```

手動で導入する場合は、[natural-japaneseのReleases](https://github.com/coji/natural-japanese/releases) から配布ファイルを取得できます。

## 使い方

対象プロジェクトを開いて依頼します。Codexでの呼び出し例です。

```text
$git-work-summary 今日のコミット履歴と変更内容を確認して、作業内容を箇条書きにまとめてください。
```

```text
$git-work-summary 2026年11月19日（日本時間）のコミットをまとめてください。作業中のタグ変更も、翌日にやることとして整理してください。
```

Claude Codeでは、`$git-work-summary` の代わりに `/git-work-summary` で呼び出します。

```text
/git-work-summary 今日のコミット履歴と変更内容を確認して、作業内容を箇条書きにまとめてください。
```

`natural-japanese` も、利用するClaude Codeから見つかる場所に導入してください。

日付の既定値は実行時の今日、対象は現在のブランチから辿れる履歴、日付の基準はコミット日時です。別ブランチや特定の作者を対象にしたい場合は依頼に書き添えてください。履歴・差分の調査は読み取り専用で、ファイル変更やコミット、外部への投稿は行いません。

## 履歴収集だけ実行する

リポジトリ直下からの例です。

```text
python skills/git-work-summary/scripts/collect_commits.py --repo /path/to/project --date 2026-11-19 --utc-offset +09:00
```

`--include-working-tree` を追加すると、ステージ済み・未ステージ・未追跡のファイル一覧も取得します。`--ref branch-name` でブランチを指定できます。出力はJSONで、要約文の生成やnatural-japaneseの実行はエージェントが担当します。

## 検証

```text
python -m unittest discover -s tests -v
```

一時リポジトリで日付境界、作者日時とコミット日時の違い、別ブランチの除外、未コミット分の分離、状態を変更しないことを確認します。報告文そのものの確認観点は [evals/scenarios.md](evals/scenarios.md) にあります。

Claude Codeのスキル仕様に沿った構成ですが、Claude Code上での読み込みと一連の動作確認はまだ行っていません。
