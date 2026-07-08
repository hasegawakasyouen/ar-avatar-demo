# 未テクスチャ装飾マテリアルの仕上げ 設計書

- 日付: 2026-07-09
- ステータス: 承認済み（brainstormingフェーズ完了）

## 背景・目的

現在、`metal`/`Diamond`/`pearl`/`tear`/`Gam`/`chain`/`Maid`の7マテリアルは実テクスチャが見つからず、既定値（灰色・非金属）のまま出力されている。元の`ririka.blend`ファイルを直接調査した結果、これらのうち5マテリアルについて、作者が実際に設定した値（テクスチャ参照・PBR値）が判明した。この情報を元に、推測ではなく元の設定を復元する。

## 調査で判明した内容

- **metal**: `cloth2_Base_color.png` というテクスチャを使用（`texture/PNG/cloth2.png`として既に存在するが、これまで未使用だった）。Bag/Boots/Cloth/髪など多くのパーツで共有される「金具・トリム」用と思われる
- **Diamond**: Base Color白(1,1,1,1)・Metallic=0・Roughness=0（テクスチャなし、ツルツルのガラス調）
- **pearl**: Diamondと同一設定
- **tear**: Emissionシェーダーのみで構成、青い放射色 (0, 0.0047, 1.0)・Strength=1.0、Blend Method=HASHED。涙形の光るチャームと思われる
- **chain**: Base Colorは既定の灰色のままだが、Metallic=0.8731...・Roughness=0.2418...（金属チェーンの質感）
- **Gam**: 元ファイルでも既定値（灰色・非金属・粗さ0.5）のまま。手がかりなし
- **Maid**: `mizuki`という別の無関係アバタープロジェクトのテクスチャを参照。現在のメッシュでは対象マテリアルの面が0件（実害なし）

## 前提・制約

- `Gam`・`Maid`は変更しない（Gamは根拠がなく、Maidは実害がないため）
- `scripts/convert_to_web.py`の既存の`MATERIAL_TEXTURE_MAP`によるテクスチャ再リンクの仕組みは維持し、そこに`metal`を追加するだけにとどめる
- `tear`のEmissionシェーダーはglTFエクスポートに適さないため、Principled BSDFノードを新規作成して置き換える

## 実装内容

### 1. `metal`をテクスチャ対象に追加

`textures/cloth2.png` を追加コピーし、`MATERIAL_TEXTURE_MAP`に以下を追加する:

```python
MATERIAL_TEXTURE_MAP = {
    "body": "body.png",
    "body_b": "body_b.png",
    "body_option": "body.png",
    "cloth": "Cloth.png",
    "cloth1": "cloth1.png",
    "Hair": "Hair.png",
    "underwear": "underwear.png",
    "metal": "cloth2.png",
}
```

### 2. 新規関数 `tune_material_pbr_values()`

テクスチャを持たない4マテリアルのPBR値を、元の`ririka.blend`で判明した実際の値に設定する:

- `Diamond`: Base Color=(1,1,1,1)、Metallic=0、Roughness=0
- `pearl`: Diamondと同一設定
- `chain`: Metallic=0.8731563091278076、Roughness=0.2418879121541977（Base Colorは変更しない）
- `tear`: 既存のノードツリーをクリアしてPrincipled BSDFノードを新規作成し、Material Outputに接続。Emission Color=(0, 0.0047, 1.0)、Emission Strength=1.0を設定

`main()`内で、`relink_material_textures()`の直後に`tune_material_pbr_values()`を呼び出す。

## 動作確認方法

1. 実際に変換を実行し、GLBのJSONを解析して各マテリアルの`baseColorFactor`/`metallicFactor`/`roughnessFactor`/`emissiveFactor`が意図した値になっていることを確認する
2. ブラウザプレビューでスクリーンショットを撮り、`tear`が青く光って見える、`chain`が金属っぽく見えることを目視確認する
3. 他のマテリアル・アニメーション・スキンに影響がないことを確認する（回帰確認）
4. `ar-avatar-demo`・`vrc-mascot-pwa`両方に反映し、実機確認する

## スコープ外（今回やらないこと）

- `Gam`・`Maid`マテリアルの変更
- `tear`のHASHEDブレンドモード（半透明）の完全な再現（今回はEmission発光のみ再現し、不透明として扱う）
