# current_tasks 運用

- ロックファイル: `current_tasks/<task>.lock`
- メタ情報: `current_tasks/<task>.lock.meta`
- メタには `owner`, `timestamp`, `ttl_minutes` を保存する。

## 基本フロー

1. `python3 harness/task_lock.py acquire <task> <owner> --ttl-minutes 120`
2. 実装 + `make check && make test_fast`
3. `python3 harness/task_lock.py release <task> <owner>`

## 期限切れ掃除

```bash
python3 harness/task_lock.py reap
```
