# iOS用VRM軽量化 — Windows実行引継ぎ

## 目的

`model.vrm`（264,502,752 bytes）はiPhone 15 Pro Max上のWKWebViewで読込開始後に
WebContentプロセスが終了した。原本を変更せず、iOS用の`model_ios.vrm`を生成して
最小vertical slice（モデル表示＋`idle.vrma`）を再試験する。

## 判明している主因

- 埋込画像: 16個、合計111,878,699 bytes
- 画像以外のbufferView: 約150,730,164 bytes
- Body: 704 shape keys × 4 primitives
- VRM全体: 3,195 morph targets、6,836 accessors
- 実際にVRM Expressionが参照するshape keyはBody上の限定された集合

## Windows側での生成

既存のBlender 5.1＋VRM Add-on v4.3.3環境を使う。元の`.blend`は保存しない。

```powershell
blender --background --python scripts/export_vrm_ririka_kaihen_ios.py -- `
  source/ririka_kaihen.blend model_ios.vrm 1024
```

スクリプトは次を行う。

1. VRM preset/custom expressionが参照するshape keyだけを保持する。
2. その他のメッシュの不要なshape keyを除去する。
3. 長辺1,024pxを超える画像を縦横比を保って縮小し、変更後ピクセルをPNGとしてpackする。
4. 既存のボーン・表情・meta設定とsparse shape key出力を使ってVRM 1.0を書き出す。

## Windows側の検証

生成ログに`IOS_SHAPE_KEYS`、`IOS_TEXTURES`、`EXPORT_RESULT: {'FINISHED'}`があることを確認する。

```powershell
Get-Item model_ios.vrm | Select-Object Name, Length
```

合格条件:

- `model_ios.vrm`が100MB未満（目標50〜80MB）
- VRM 1.0として読める
- humanoid、skin、preset expressions、custom `joy`／`crying`が残る
- 黒猫悪夢衣装、髪、顔、透過表現に明白な破綻がない
- 原本`model.vrm`と`source/ririka_kaihen.blend`が変更されていない

生成物はGitへ追加せず、Mac側リポジトリ直下へ`model_ios.vrm`として渡す。
Mac側ではiOSターゲットのモデル参照を一時的に同ファイルへ切り替え、実機で
`model-loaded`、`idle-loaded`、`MASCOT_READY`、プロセス生存を確認する。

## 失敗時

- 必須shape key不足: 削除処理へ進まず停止するため、ログのmesh/key名をMac側へ返す。
- 100MB以上: まず512px版を別名で生成して比較し、メッシュ削減はその後に判断する。
- 見た目破綻: 原本へ上書きせず、1,024px版を破棄して対象テクスチャだけ2,048pxへ戻す。
