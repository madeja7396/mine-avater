## Skills
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file. Below is the list of project skills available in this repository.

### Available skills
- avatar-development-orchestrator: 日々の実装ループを統制し、タスクロック・品質ゲート・収束チェックを運用する。 (file: /root/dev/mine-avater/skills/avatar-development-orchestrator/SKILL.md)
- avatar-ci-guardian: CI失敗ログを解析し、再現コマンドと最小修正順序へ落とし込む。 (file: /root/dev/mine-avater/skills/avatar-ci-guardian/SKILL.md)
- avatar-spec-steward: specs/eval/ci の整合を維持し、閾値・契約ドリフトを防ぐ。 (file: /root/dev/mine-avater/skills/avatar-spec-steward/SKILL.md)

### How to use skills
- Discovery: まず必要スキルの `SKILL.md` を開いて、手順と参照ファイルを確認する。
- Progressive disclosure: `SKILL.md` の指示で必要な `scripts/` と `references/` のみ読む。
- Validation: スキルを更新したら `quick_validate.py` を実行して整合性を確認する。
- Scope: 長期開発では、実装系は `avatar-development-orchestrator`、障害対応は `avatar-ci-guardian`、仕様同期は `avatar-spec-steward` を使い分ける。

### Routing rules (mandatory)
- 実装タスク開始時は `avatar-development-orchestrator` を最初に使う。
- CI失敗の解析は `avatar-ci-guardian` を最初に使う。
- 仕様・閾値・インタフェース更新は `avatar-spec-steward` を最初に使う。
- 複合タスクでは以下の順序で使う。
1. `avatar-ci-guardian`（失敗原因の特定）
2. `avatar-spec-steward`（仕様同期が必要な場合）
3. `avatar-development-orchestrator`（修正実装と最終ゲート）

### Operational guardrails
- 実装前に `make check` を通す。
- 変更後に `make test_fast` と `make test_unit` を通す。
- 仕様や評価に関わる変更は `make test_full` まで通す。
- ロック対象作業では `harness/task_lock.py` で acquire/release を行う。
