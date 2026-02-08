# 現状ステータス（2026-02-08）

最終更新日時: 2026-02-08  
ブランチ: `main`  
HEAD: `d3b3a93`

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
- Phase 4: augmentation と過学習抑制（初手）
  - `--vit-enable-reference-augmentation`, `--vit-augmentation-copies`, `--vit-augmentation-strength` 追加
  - 参照特徴の仮想augmentation（決定的ジッタ）を conditioning 融合へ適用
  - `--vit-overfit-guard-strength` で中立条件への収縮を導入し、過学習的偏りを抑制
- Phase 6: 透かし標準化
  - Postprocessor 既定で `output.mp4.watermark.json` を生成
  - `output.mp4.meta.json` に `watermark_id`, `watermark_policy_version`, `watermark_manifest` を記録
  - `--disable-watermark`, `--watermark-label` で透かし動作を制御
- Phase 6: 研究用途ポリシー文書化
  - `docs/research-use-policy.md` を追加
  - `README.md` / `CONTRIBUTING.md` から参照導線を追加
- CI監視/障害トリアージ
  - `ci/monitor_ci.py`
  - 失敗ジョブのログ取得 + `skills/avatar-ci-guardian/scripts/triage_ci_log.py` 実行
- CI耐障害性の改善
  - `pipeline/image_io.py` の ffmpeg 呼び出しで `FileNotFoundError` / `OSError` を吸収
  - ffmpeg 未導入環境でも PNG/byte fallback へ遷移し、`vit-mock` smoke が継続可能
  - ジョブログAPI権限不足時は jobs/steps から fallback triage ログを生成
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
- `test_unit` 成功（56 tests）
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
結果: 最新runは成功（triage は権限不足時fallback対応済み）

- 最新CI run: `21795837689`（`conclusion=success`）
- SHA: `d3b3a93b3271162db2aba8fe557e56ac82e49c3a`
- 以前の失敗（`Run vit-mock smoke test`）は ffmpeg 非存在時の `FileNotFoundError` を修正済み
- 補足: failed run のジョブログ自動取得は引き続きトークン権限（admin rights）に依存するが、
  権限不足時でも fallback triage で失敗ステップ分類は可能

## 4. 再開手順（次回セッション開始時）

1. `make monitor_ci_watch` でCIグリーンを確認
2. `make test_all` でローカル回帰確認
3. 研究用途ポリシーと透かし運用を前提に運用継続
4. 必要に応じて `repo` 管理者権限相当トークンで実ジョブログtriageを有効化

## 5. 直近コミット履歴

- `af8b85e` fix: harden vit smoke fallback and add temporal-spatial proxy
- `d3b3a93` feat: start phase4 augmentation and overfit guard
- `3ccfbbb` docs: finalize current status after CI green
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
