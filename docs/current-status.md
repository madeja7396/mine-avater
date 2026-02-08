# 現状ステータス（2026-02-08）

最終更新日時: 2026-02-08  
ブランチ: `main`  
HEAD: `3e67bd1`

## 1. 実装済み

- プロジェクト基盤（`specs/`, `eval/`, `ci/`, `harness/`, `pipeline/`, `tests/`, GitHub Actions CI）
- タスクロック運用（`harness/task_lock.py`）
- 評価ランナー/資産チェック（`ci/eval_runner.py`, `ci/check_*`）
- パイプライン骨格の実動作
  - 前処理: `audio_features.npy`, `mouth_landmarks.json` 生成
  - 生成: フレーム列 `frames/*.png` 生成
  - 後処理: `ffmpeg` 優先で `output.mp4` 生成、失敗時はプレースホルダ
- ViTバックエンド
  - `heuristic`, `vit-mock`, `vit-hf`, `vit-auto`
  - `vit-auto` は実ViT不可時に `vit-mock-fallback`
- multi-view ViT条件付け
  - `--vit-reference-dir`, `--vit-reference-limit` 追加
  - 参照画像 + 追加参照画像を融合して conditioning 算出
- 3D-aware条件付け（検証向け）
  - `--vit-enable-3d-conditioning`, `--vit-3d-conditioning-weight` 追加
  - mouth landmarks から mock 3D パラメータ（yaw/pitch/depth）を推定して ViT conditioning に融合
  - `pipeline_run.json` の generator stage に 3D-aware 設定を記録
- 時空間損失（検証向け）
  - `--temporal-spatial-loss-weight`, `--temporal-smooth-factor` 追加
  - 口ランドマークから temporal-spatial loss proxy を算出し、口開閉をフレーム間で平滑化
  - `pipeline_run.json` の generator stage に loss 関連設定を記録
- CI監視/障害トリアージ
  - `ci/monitor_ci.py`
  - 失敗ジョブのログ取得 + `skills/avatar-ci-guardian/scripts/triage_ci_log.py` 実行
- CI耐障害性の改善
  - `pipeline/image_io.py` の ffmpeg 呼び出しで `FileNotFoundError` / `OSError` を吸収
  - ffmpeg 未導入環境でも PNG/byte fallback へ遷移し、`vit-mock` smoke が継続可能
- `.env.lock` 運用整備
  - `.env.lock.example` 追加
  - `.env.lock` を `.gitignore` で除外
  - `monitor_ci` 側で `export GITHUB_TOKEN=...` 記法も読込可能

## 2. テスト結果（この更新時点の実行結果）

実行コマンド: `make test_all`  
結果: 成功

- `lint` 成功
- `check` 成功
- `test_fast` 成功
  - `lipsync_mae_mean=0.0838`
  - `mouth_breakage_rate_mean=0.0158`
  - `temporal_jump_mean=0.0416`
  - `psnr_mean=31.1600`
  - `ssim_mean=0.9466`
  - `throughput_fps=21.50`
- `test_unit` 成功（47 tests）
- `test_smoke` 成功
- `test_vit_smoke` 成功
- `test_full` 成功
  - `lipsync_mae_mean=0.0833`
  - `mouth_breakage_rate_mean=0.0194`
  - `temporal_jump_mean=0.0422`
  - `psnr_mean=30.8625`
  - `ssim_mean=0.9429`
  - `throughput_fps=18.40`

## 3. CI監視の現状

実行コマンド: `make monitor_ci` / `make monitor_ci_triage`  
結果: 最新run検出は成功、failed jobs のログ取得は権限不足で失敗（GitHub API 403）

- 最新CI run: `21795298189`（`validate (3.11)` / `validate (3.12)` が failure）
- jobs API では失敗ステップが `Run vit-mock smoke test` と判明
- ローカル再現（ffmpeg 非存在 PATH）で `FileNotFoundError: ffmpeg` を確認し、fallback修正を実装済み
- エラー: `ci_auto_triage_log_fetch_failed ... status=403 (Must have admin rights to Repository)`
- `.env.lock` のトークン設定により run一覧取得は成功。ジョブログ取得には追加権限が必要

## 4. 再開手順（次回セッション開始時）

1. `repo` 管理者権限相当のトークンに更新（job logs API が 403 を返さない権限）
2. `make monitor_ci_triage` を再実行して failed jobs のログ取得/triageを確認
3. `make test_all` で回帰確認
4. 修正を push して CI 再実行し、`Run vit-mock smoke test` の再発有無を確認
5. 本実装を `specs/roadmap.md` の Phase 4（augmentationと過学習抑制）から継続

## 5. 直近コミット履歴

- `3e67bd1` docs: snapshot current implementation and handoff status
- `ee399f8` feat: add multi-view vit conditioning and secure env lock flow
- `524fcee` feat: support CI failure auto-triage with job log retrieval
- `2614c3a` feat: auto-triage failed CI jobs from monitor command
- `d65f96d` feat: add GitHub Actions CI status monitoring commands
- `5d1a3a1` ci: add vit-mock smoke gate for generator backend
- `325a8b2` feat: implement ViT-ready image conditioning with real image decoding
- `1170058` feat: add optional ViT generator backends with runtime selection
- `fc699d2` ci: add scaffold smoke test to validate runtime wiring
- `42ac5dc` feat: add configurable pipeline runner and stage orchestration
- `2792e27` feat: implement scaffold preprocess, generator, and postprocess stages
- `71cacfb` chore: bootstrap project foundation, CI, and skills
