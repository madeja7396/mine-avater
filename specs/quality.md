# 品質基準（SSOT）

本ファイルは `avatar_pipeline` の機械判定基準を定義する。
機械判定に使うしきい値の正本は `specs/quality_thresholds.json` とする。

## 1. 目的

- リップシンク誤差、口領域破綻、時間的一貫性、処理健全性を自動で判定する。
- `fast` で高頻度回帰検知、`full` で収束確認を行う。

## 2. 指標

- `lipsync_mae`（小さいほど良い）
- `mouth_breakage_rate`（小さいほど良い）
- `temporal_jump`（小さいほど良い）
- `psnr`（大きいほど良い）
- `ssim`（大きいほど良い）
- `oom_rate`（小さいほど良い）
- `failure_rate`（小さいほど良い）
- `throughput_fps`（大きいほど良い）

## 3. しきい値（初期）

- `lipsync_mae <= 0.120`
- `mouth_breakage_rate <= 0.050`
- `temporal_jump <= 0.080`
- `psnr >= 30.0`
- `ssim >= 0.930`
- `oom_rate <= 0.010`
- `failure_rate <= 0.020`
- `throughput_fps >= 12.0`

## 4. 実行モード

- `fast`: 固定サンプルによる短時間評価（常時）
- `full`: 全量または広い固定集合での評価（収束フェーズ）

## 5. ログ規約

- 先頭行は必ずサマリを出力する。
- 失敗時は `ERROR:`、正常時は `METRIC:` のプレフィクスを使う。
