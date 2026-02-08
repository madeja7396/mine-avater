# mine-avater

`docs/shoki-keikaku.md` と `docs/project-policy.md` に基づく、アバタ動画生成プロジェクトの基盤です。

## 目的

- 音声/画像入力から `avatar_pipeline` で動画を生成する。
- 品質を機械判定し、エージェント並列開発でも収束しやすい形にする。
- 初期目標として PSNR/SSIM を改善し、時間的一貫性と口周り安定性を維持する。

## 構成

- `current_tasks/`: タスクロック管理
- `specs/`: SSOT仕様（品質基準・インタフェース）
- `harness/`: エージェント向け運用スクリプト
- `pipeline/`: 実装本体（現時点は契約定義）
- `eval/fast`, `eval/full`: 決定的評価データ
- `ci/`: 評価ランナー
- `tests/`: 基盤テスト

## 主要コマンド

```bash
make lint
make check
make test_fast
make test_smoke
make test_vit_smoke
make test_full
make test_unit
```

```bash
# フルゲート（CI相当）
make test_all
```

```bash
# 実装前の配線確認（ダミー実行）
python3 pipeline/run_scaffold.py \
  --input-audio /path/to/input.wav \
  --reference-image /path/to/face.png \
  --workspace /tmp/avatar-work \
  --generator-backend heuristic \
  --frame-count 12 \
  --fps 25 \
  --window-ms 25 \
  --hop-ms 10
```

`ffmpeg` が使える環境では `output.mp4` を実動画として生成し、使えない環境ではプレースホルダ出力にフォールバックします。
`--generator-backend` は `heuristic` / `vit-mock` / `vit-hf` / `vit-auto` を選択できます。`vit-hf` / `vit-auto` は `torch` と `transformers` が利用可能な場合に実ViTを使い、不可能な場合は設定に応じて `vit-mock` にフォールバックします。

```bash
# タスクロック取得
python3 harness/task_lock.py acquire mouth_roi_stabilize agent-01 --ttl-minutes 120

# タスクロック解放
python3 harness/task_lock.py release mouth_roi_stabilize agent-01

# 期限切れロック掃除
python3 harness/task_lock.py reap
```

## ガイドライン

- 開発ガイド: `docs/guidelines/development.md`
- テスト/CI運用: `docs/guidelines/testing-ci.md`
- 参加方法: `CONTRIBUTING.md`
- アーキテクチャ外枠: `specs/architecture.md`

## Skills

- スキル一覧: `AGENTS.md`
- 実装ループ: `skills/avatar-development-orchestrator/SKILL.md`
- CI障害対応: `skills/avatar-ci-guardian/SKILL.md`
- 仕様同期: `skills/avatar-spec-steward/SKILL.md`
- ルーティング規約: `AGENTS.md` の `Routing rules (mandatory)` を常に適用
