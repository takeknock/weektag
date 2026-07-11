# weektag

タグ式のCLIタイムトラッカー。記録はエージェント可読な週別JSONLに保存。

[English README](README.md)

`weektag` は作業を start/stop の区間としてフラットなタグ付きで記録し、ISO週ごとの
プレーンな JSONL ファイルに保存します。週次レポートや、Excel にそのまま貼れる
TSV/CSV に変換できます。ファイルがデータベースのすべてであり、`cat` / `grep` /
`jq`、そして Claude Code などのコーディングエージェントが前処理なしで読めます。
手編集も正式サポートです。

```console
$ tt start writing client-a -m "ブログ下書き"
started writing client-a "ブログ下書き" at 09:00 [KZ3M2A7Q]

$ tt status
running: writing client-a "ブログ下書き" (started 09:00, 1.50 h elapsed) [KZ3M2A7Q]

$ tt stop
stopped writing client-a "ブログ下書き" (1.50 h)
```

## インストール

```console
pipx install weektag    # または: uv tool install weektag
```

インストールされるコマンドは `tt` です（PyPI の `tt` は取得済みのため配布名は
`weektag`）。Python 3.11 以上が必要です。

## コマンド

```
tt start <tags...> [-m メモ] [--at 9:00]   # 開始（実行中があれば自動stop）
tt stop [--at 10:30]                       # 停止
tt status                                  # 実行中タスクと経過時間
tt resume                                  # 直前タスクを同タグ・同メモで再開
tt add 9:00-10:30 <tags...> [-m メモ]      # 後追いの区間追加
tt edit <id前方一致> [--start] [--stop] [--tags] [-m]
tt rm <id前方一致>                         # 削除
tt cancel                                  # 実行中を記録せず破棄
tt log [--week 2026-W27]                   # id付き生ログ（editの入口）
tt report [--week 2026-W27 | --last]       # タグ別の週次集計
tt export [--format csv] [-o FILE] [--no-header]
tt export --daily [--date 7/6] [--noon 13:00] [--round 0.25] [--header]
```

同時に実行できるタスクは常に1本だけです。実行中に `tt start` すると前のタスクを
止めてから開始します。打ち忘れ・止め忘れは `add` / `edit` / `rm` で後から直せます。

シェル補完（bash / zsh / fish）。直近の記録からのタグ動的補完つき：

```console
tt --install-completion
```

## データ形式

1行=1 JSONオブジェクト、1ファイル=1 ISO週（月曜始まり）。保存先は
`~/.local/share/weektag/events/`（`WEEKTAG_DATA_DIR` で変更可、
`XDG_DATA_HOME` にも対応）：

```json
{"id":"KZ3M2A7Q","start":"2026-07-06T09:00:00+09:00","stop":"2026-07-06T10:30:00+09:00","tags":["writing","client-a"],"note":"ブログ下書き"}
```

- 実行中タスクは `stop` キーを持たないレコードです。
- 時刻はローカル時刻＋UTCオフセット。週の帰属は `start` のローカル日付で決まり、
  週を跨ぐレコードも分割しません。
- 週ファイルが唯一の真実です。隠れた状態ファイル・インデックス・DBはありません。
  手やエージェントでいつでも編集できます。

### ISO週年についての注意

ファイル名は ISO 8601 週番号なので、年末年始で暦年とズレることがあります。
例：2027-01-01 のレコードは `2026-W53.jsonl` に入ります。コマンドは正しく
解決するので、手でファイルを探すときだけ気にしてください。

## Excel との連携

`tt export` は十進時間（`1.50`）の TSV（`date start stop hours tags note`）を
出力するので、Excel に貼ると列が自動で分かれ、SUM がそのまま効きます。

`tt export --daily` は日報転記用プリセットです：3列だけ（概要 / 午前実績 /
午後実績）、その日の「タグ集合＋メモ」ごとに集約、正午で機械分割（`--noon` で
変更可）、既存の表に日々貼るためヘッダーは既定で出しません。予定列は出力しない
ので、右端の予定列を上書きしません。クリップボード連携は内蔵せず、パイプで：

```console
tt export --daily | clip        # Windows
tt export --daily | pbcopy      # macOS
tt export --daily | xclip -sel c
```

## コマンド名の衝突

`tt-time-tracker` パッケージも `tt` コマンドをインストールします。pipx / uv では
環境自体は隔離され、PATH 上でのみ衝突します。両方使う場合はシェルエイリアスで
どちらかを改名してください（例：`alias wt=tt`）。

## 開発

```console
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

MIT ライセンス。
