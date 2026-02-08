# Contributing

本プロジェクトは、`docs/project-policy.md` の方針に従ってエージェント並列開発を行います。
利用時は `docs/research-use-policy.md` の研究用途制限を遵守してください。

## 1. 開発開始前

1. `make check` を実行して基盤状態を確認する。
2. `python3 harness/task_lock.py acquire <task> <owner> --ttl-minutes 120` で担当を確保する。
3. 仕様変更を伴う場合は `specs/` を先に更新する。

## 2. 実装ルール

1. 1タスク1目的で変更を小さく保つ。
2. 中間成果物契約は `specs/interfaces.md` を破らない。
3. ログは `ERROR:`, `WARN:`, `METRIC:` プレフィクスを使う。
4. 破壊的変更では `eval/fast` と `eval/full` を同時更新する。

## 3. ローカル検証

```bash
make lint
make check
make test_fast
make test_unit
```

必要時:

```bash
make test_full
```

## 4. CIルール

1. PRは `validate` ジョブ成功が必須。
2. `full` は `main` / 手動実行 / 定期実行で確認する。
3. 失敗時はログ先頭の `ERROR:` 行を基点に切り分ける。

## 5. タスク終了

1. `python3 harness/task_lock.py release <task> <owner>` でロック解放。
2. しきい値変更時は `specs/quality_thresholds.json` と `specs/quality.md` を同時更新。
