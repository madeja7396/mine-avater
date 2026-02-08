# テスト・CIガイドライン

## テスト層

- `lint`: 構文・最低限の静的検証
- `check`: 基盤構造と評価資産の整合性検証
- `test_fast`: 高頻度回帰検知
- `test_smoke`: 実行配線スモーク（CLI経由で成果物生成を検証）
- `test_vit_smoke`: `vit-mock` バックエンドの統合スモーク
- `test_unit`: ユニット検証
- `monitor_ci`: GitHub Actionsの最新実行状態を確認
- `monitor_ci_watch`: CI完了まで監視し、失敗時にエラー終了
- `monitor_ci_triage`: 失敗時にジョブログを取得して自動triage実行
- `monitor_ci_watch_triage`: 監視 + 失敗時自動triage
- 監視系は `GITHUB_TOKEN` を環境変数または `.env.lock` から参照する
- `test_full`: 収束フェーズ検証
- `pipeline/run_scaffold.py`: 実装前の配線スモーク（ユニットで検証）

## 運用方針

- 開発中は `make test_fast` を最優先で回す。
- PR前に `make lint && make check && make test_unit` を必須実行する。
- `full` は重い検証として main と定期実行で担保する。

## 失敗時の切り分け

1. 先頭の `ERROR:` を確認
2. しきい値不一致なら `specs/quality_thresholds.json` と `eval/*/samples.json` を整合
3. 構造不一致なら `ci/check_scaffold.py` の不足項目を修正
