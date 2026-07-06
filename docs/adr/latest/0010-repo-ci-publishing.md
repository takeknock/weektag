# 0010. リポジトリ構成・CI・公開フロー

## ステータス
Accepted

## コンテキスト
本ツールのバグは時刻起因（週境界・正午分割・ISO 週年の W53 問題・タイムゾーン・日跨ぎ）に集中すると予想される。また Windows での動作（パス、`os.replace` の原子性、コンソール出力）は使う人が必ずいる一方、開発環境では検証できない可能性が高い。

## 決定
- **src レイアウト**（`src/weektag/`）、ビルドバックエンドは **hatchling**、設定は pyproject.toml に集約
- 開発ツール：**uv**（環境・ロック）、**ruff**（lint / format）、**pytest ＋ freezegun**（時刻固定テスト）。dev 依存はランタイム依存と分離する
- **GitHub Actions**：push / PR 毎に ubuntu / macos / windows × Python 3.11–3.13 のマトリクスでテスト
- 公開は **PyPI Trusted Publishing**（OIDC）。git タグを push → Actions がビルドして公開。API トークンは保持しない
- ライセンスは **MIT**
- README は英語主体＋日本語版（`README.ja.md`）を併置

## 結果
- 週境界・W53・正午按分などのエッジケースを freezegun で決定的にテストできる
- Windows 対応が公開前に CI で機械的に担保される
- トークン漏洩リスクが構造的に存在しない公開フローになる
