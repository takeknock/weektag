# ADR — Architecture Decision Records

weektag の設計決定記録。2026-07-06 の設計セッション（grill-me 形式の一問一答）で確定した内容を記録する。

実装・レビュー・後続の設計相談では、このディレクトリを設計の唯一の正典として参照すること。

## 運用ルール

- 新しい決定は `latest/` に連番で追加する。**番号は振り直さない**
- 決定を変更する場合：旧版を `archive/{NNNN}/` に退避してから、新しい番号で新版を書く
- 各 ADR は「ステータス / コンテキスト / 決定 / 結果」の4部構成

## 索引

| # | タイトル | 要旨 |
|---|---------|------|
| [0001](latest/0001-cli-first-positioning.md) | CLIファーストの立ち位置 | エージェント可読な時間記録を差別化軸に |
| [0002](latest/0002-recording-model.md) | 記録モデル | start/stop型＋後追い修正、同時実行は常に1本 |
| [0003](latest/0003-weekly-jsonl-storage.md) | ストレージ | 週別JSONL・ISO週・月曜始まり・ファイルが唯一の真実 |
| [0004](latest/0004-record-schema.md) | レコードスキーマ | 構造化タグ・ローカル時刻＋オフセット・ミニULID |
| [0005](latest/0005-v1-command-set.md) | v1コマンドセット | start〜export の11コマンド。目標・タイマーは対象外 |
| [0006](latest/0006-report-export-split.md) | report/export分離 | 集計表と行データ出力の役割分離、十進時間 |
| [0007](latest/0007-daily-export-preset.md) | 日報プリセット | `--daily` 3列TSV・正午分割・予定列は出さない |
| [0008](latest/0008-naming-weektag-tt.md) | 名前 | 配布名 weektag、コマンド tt |
| [0009](latest/0009-stack-typer-py311.md) | 技術スタック | typer・Python 3.11+・依存最小・出力はプレーン |
| [0010](latest/0010-repo-ci-publishing.md) | 開発・公開基盤 | src+hatchling・uv/ruff/pytest・3OS CI・Trusted Publishing |
