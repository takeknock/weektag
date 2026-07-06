# 0009. typer 採用・Python 3.11+・依存は最小

## ステータス
Accepted

## コンテキスト
「どんな環境でも」動くには依存は少ないほど良い。当初はランタイム依存ゼロ（argparse）を推奨したが、**シェル補完が日常使用の要件**として確定した。argparse で補完を自作・保守するコストは高く、typer なら補完と整った `--help` が実質タダで手に入る。

## 決定
- CLI フレームワークは **typer**。ランタイム依存は typer（同梱の rich / shellingham を含む）のみとする
- `tt --install-completion` による bash / zsh / fish 補完を提供する
- **タグ名の動的補完を v1 に含める**：`tt start wri<TAB>` で直近数週の週ファイルからタグ候補を提示（typer の autocompletion コールバック）
- rich による装飾出力は**使わない**。report / export はプレーンテキスト（0006）
- サポートは **Python 3.11 以上**
- 現在時刻の取得は `datetime.now().astimezone()`（外部 tzdata 不要でローカルオフセット付き時刻が得られ、Windows でも追加依存が要らない）
- ID 生成（ミニULID）は自作する（0004）
- 設定ファイルは v1 では持たない。環境変数（`WEEKTAG_DATA_DIR`）とコマンドフラグ（`--noon`、`--round` 等）で賄う

## 結果
- 補完・ヘルプの品質を低コストで確保できる
- 依存が typer 系に閉じるため、供給網リスクとバージョン衝突リスクは小さいまま
- 3.11+ により、将来設定ファイルを導入する際は標準の `tomllib` が使える
