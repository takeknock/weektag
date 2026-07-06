# 0008. 配布名 weektag、コマンド名 tt

## ステータス
Accepted

## コンテキスト
PyPI の `tt` は Tensor Train 形式のパッケージに取得済みで使用不可。さらに先行の Python 製 CLI タイムトラッカー `tt-time-tracker` が存在し、インストールされるコマンド名として `tt` を使用している。一方、毎日何度も打つツールにとって2打鍵コマンドの価値は大きく、本プロジェクトの入力設計はすべて `tt` を前提にしている。

## 決定
- PyPI 配布名・import 名・GitHub リポジトリ名：**`weektag`**
- コンソールコマンド：**`tt`**

```toml
[project.scripts]
tt = "weektag.cli:main"
```

- データディレクトリも `~/.local/share/weektag/` として名前を揃える（0003）
- 実装の初手で pypi.org/project/weektag が未取得（404）であることを確認してから最終確定する

## 結果
- httpie → `http` と同じ「配布名≠コマンド名」構造になる
- `tt-time-tracker` とはコマンド名が衝突しうる。pipx / uv では環境自体は隔離され、PATH 上の共存のみが問題。ニッチ同士のため許容する
- README に衝突の可能性と回避策（シェルエイリアスでの改名）を明記する
