# 中間成果物インタフェース（SSOT）

並列実装時の衝突を減らすため、中間成果物を固定する。

## 1. 入力

- `input_audio`: 音声ファイル（例: wav）
- `reference_image`: 参照顔画像

## 2. 中間成果物

- `audio_features.npy`
  - 内容: 音素/韻律特徴の系列
  - 形状: `[T, D]`
- `mouth_landmarks.json`
  - 内容: フレームごとの口周辺ランドマーク
  - 形式: `{"frame_index": int, "points": [[x, y], ...]}[]`
- `frames/`
  - 内容: 生成された連番フレーム（png）

## 3. 出力

- `output.mp4`
  - 音声付き最終動画

## 4. 互換ポリシー

- 既存キー・ファイル名は後方互換を維持する。
- 破壊的変更時は `specs/` の更新と `eval` の更新を同時に行う。

