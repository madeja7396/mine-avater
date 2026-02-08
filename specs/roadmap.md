# 実装ロードマップ（初期計画反映）

`docs/shoki-keikaku.md` の初期計画を実装タスクへ分解した。

## Phase 1: セットアップ

- [x] ベース実装の検証可能な骨格を維持
- [x] `fast/full` 評価導線を固定

## Phase 2: ViTバックボーン統合

- [x] エンコーダをViT中心へ拡張（`vit-mock` / `vit-hf` / `vit-auto`）
- [x] 必要に応じてローカル特徴抽出器を併用（mock/fallback経路）

## Phase 3: 参照動画の空間表現

- [~] multi-view特徴融合（参照画像群の融合を実装済み）
- [ ] 3D-aware条件付けの検証
- [ ] 時空間損失の導入

## Phase 4: クローン元データ強化

- [~] multi-referenceデータ運用（入力経路の実装済み）
- [ ] augmentationと過学習抑制

## Phase 5: 評価と最適化

- [x] PSNR/SSIM/時系列一貫性の継続測定（`eval_runner`）
- [~] 失敗率/OOM率/速度の運用監視（ローカル監視実装済み、GitHub API認証調整が未完）

## Phase 6: 倫理・公開

- [ ] 透かし付与を標準化
- [ ] 研究用途ポリシーと利用制限を文書化

進捗の詳細は `docs/current-status.md` を参照。
