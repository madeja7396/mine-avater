# アーキテクチャ外枠

## 1. ステージ構成

1. `Preprocessor`
2. `Generator`
3. `Postprocessor`

契約は `pipeline/contracts.py` を正本とする。
雛形実装は `pipeline/scaffold.py`、実行エントリは `pipeline/run_scaffold.py`。
補助実装として `pipeline/preprocess.py`, `pipeline/generator.py`, `pipeline/postprocess.py` を持つ。
実行制御は `pipeline/engine.py`、ステージ設定は `pipeline/config.py` で管理する。
Generatorは `heuristic` と `ViT系バックエンド（vit-mock / vit-hf / vit-auto）` の切替を持つ。
画像デコードは `pipeline/image_io.py` を介して行い、`ffmpeg` 優先・PNGデコーダ/バイトフォールバックを備える。

## 2. 中間成果物

- `audio_features.npy`
- `mouth_landmarks.json`
- `frames/`

命名と役割は `specs/interfaces.md` に従う。

## 3. 実装着手ルール

- 実ステージ実装は契約を壊さない範囲で追加する。
- 破壊的変更は `specs/interfaces.md` と `tests/` を同時更新する。
- 実装前に `make check` を通すこと。

## 4. 品質ゲート

- `make lint`
- `make check`
- `make test_fast`
- `make test_unit`
- `make test_full`（main/手動/定期）
