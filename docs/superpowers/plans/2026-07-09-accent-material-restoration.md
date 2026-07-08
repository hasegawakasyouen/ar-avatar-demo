# 未テクスチャ装飾マテリアルの仕上げ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `metal`/`Diamond`/`pearl`/`tear`/`chain`の5マテリアルを、元の`ririka.blend`で判明した実際の値（テクスチャ・PBR値）で正しく表示させる。

**Architecture:** `scripts/convert_to_web.py`の`MATERIAL_TEXTURE_MAP`に`metal`を追加し、新規関数`tune_material_pbr_values()`でDiamond/pearl/chain/tearのPBR値を設定する。既存の変換パイプライン（テクスチャ再リンク・アニメーション合成）には影響を与えない。

**Tech Stack:** Blender 4.5（bpy headless script）

**確認済みの環境:**
- `D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\texture\PNG\cloth2.png`（`metal`マテリアル用の実テクスチャ、読み取り専用として扱う）
- `scripts/convert_to_web.py`は現在、`MATERIAL_TEXTURE_MAP`（テクスチャ再リンク）と`harvest_extra_animations()`（アニメーション合成）を持つ

---

### Task 1: `metal`用テクスチャを追加し、`MATERIAL_TEXTURE_MAP`を拡張する

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\textures\cloth2.png`
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\scripts\convert_to_web.py`

- [ ] **Step 1: cloth2.pngをコピーする**

```bash
cp "D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\texture\PNG\cloth2.png" "C:\Users\PC_User\Documents\ar-avatar-demo\textures\cloth2.png"
```

- [ ] **Step 2: `MATERIAL_TEXTURE_MAP`に`metal`を追加する**

現在の`MATERIAL_TEXTURE_MAP`（`scripts/convert_to_web.py`冒頭）に以下の1行を追加する:

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

（既存の7行はそのまま、`"metal": "cloth2.png"` を末尾に追加するだけ）

- [ ] **Step 3: スモークテストで後方互換性を確認**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\convert_to_web.py -- --smoketest smoketest.glb smoketest.usdz
```

Expected: `CONVERT_OK smoketest.glb smoketest.usdz`、終了コード0（`metal`マテリアルはデフォルトCubeシーンには存在しないため、この変更で壊れないはず）。確認後、生成ファイルは削除してよい。

- [ ] **Step 4: コミット**

```bash
git add textures/cloth2.png scripts/convert_to_web.py
git commit -m "feat: add real cloth2.png texture for the metal material"
```

---

### Task 2: `tune_material_pbr_values()`を追加する

**Files:**
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\scripts\convert_to_web.py`

- [ ] **Step 1: 新規関数を追加する**

`relink_material_textures()`関数の直後に、以下の関数を追加する:

```python
def tune_material_pbr_values():
    for mat_name in ("Diamond", "pearl"):
        mat = bpy.data.materials.get(mat_name)
        if mat is None or not mat.use_nodes:
            continue
        bsdf = next(
            (n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None
        )
        if bsdf is None:
            continue
        bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 0.0

    chain = bpy.data.materials.get("chain")
    if chain is not None and chain.use_nodes:
        bsdf = next(
            (n for n in chain.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None
        )
        if bsdf is not None:
            bsdf.inputs["Metallic"].default_value = 0.8731563091278076
            bsdf.inputs["Roughness"].default_value = 0.2418879121541977

    tear = bpy.data.materials.get("tear")
    if tear is not None and tear.use_nodes:
        node_tree = tear.node_tree
        for node in list(node_tree.nodes):
            node_tree.nodes.remove(node)
        output = node_tree.nodes.new("ShaderNodeOutputMaterial")
        bsdf = node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Emission Color"].default_value = (0.0, 0.0047, 1.0, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 1.0
        node_tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
```

**重要 — 実装者への注意:** `tear`の処理で使う`"Emission Color"`・`"Emission Strength"`という入力ソケット名は、Blender 4.x のPrincipled BSDFに標準搭載されているはずだが、実際にBlenderで実行してエラーが出た場合（ソケット名が違う等）は、Blender内のPythonコンソールで`bsdf.inputs.keys()`を確認し、正しい名前に修正すること。この検証はTask 3で実データを使って行う。

- [ ] **Step 2: `main()`内で呼び出す**

`main()`関数内の`relink_material_textures(TEXTURES_DIR)`の直後に、以下を追加する:

```python
        relink_material_textures(TEXTURES_DIR)
        tune_material_pbr_values()
```

- [ ] **Step 3: スモークテストで後方互換性を確認**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\convert_to_web.py -- --smoketest smoketest.glb smoketest.usdz
```

Expected: `CONVERT_OK smoketest.glb smoketest.usdz`、終了コード0（デフォルトCubeシーンには対象マテリアルが存在しないため、`tune_material_pbr_values()`は何もせず安全にスキップされるはず）。確認後、生成ファイルは削除してよい。

- [ ] **Step 4: コミット**

```bash
git add scripts/convert_to_web.py
git commit -m "feat: restore Diamond/pearl/chain/tear PBR values from original ririka.blend"
```

---

### Task 3: 実データで変換・検証する

**Files:**
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\model.glb`
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\model.usdz`

- [ ] **Step 1: 実際の変換を実行する（既存の3アニメーション合成込み）**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\convert_to_web.py -- source\avatar_idle_mixamo.fbx model.glb model.usdz source\avatar_wave_mixamo.fbx source\avatar_dance_mixamo.fbx
```

Expected: `CONVERT_OK model.glb model.usdz`

- [ ] **Step 2: GLBのJSONを解析し、各マテリアルの値を確認する**

- `metal`マテリアルが実テクスチャ（`images`配列内の実サイズの画像）を参照していること
- `Diamond`・`pearl`の`baseColorFactor`が`[1,1,1,1]`前後、`metallicFactor`が0、`roughnessFactor`が0前後であること
- `chain`の`metallicFactor`が約0.873、`roughnessFactor`が約0.242であること
- `tear`に`emissiveFactor`（青系の値）が設定されていること
- 既存の3アニメーション（idle/wave/dance）・33ジョイントのスキン・他の6テクスチャが引き続き正しいこと（回帰確認）

- [ ] **Step 3: ブラウザプレビューで目視確認する**

ローカルサーバーで`model.glb`を表示し、スクリーンショットを撮る。`tear`が青く光って見える、`chain`が金属っぽい光沢に見えることを確認する（正確な見た目は距離・角度に依存するため、「明らかに以前の灰色一色とは違う見た目になっている」ことを確認できれば十分）。

- [ ] **Step 4: コミット**

```bash
git add model.glb model.usdz
git commit -m "asset: apply restored accent material values to model.glb/usdz"
```

---

### Task 4: `ar-avatar-demo`をpushし、`vrc-mascot-pwa`にも反映する

**Files:**
- Modify: `C:\Users\PC_User\Documents\vrc-mascot-pwa\model.glb`（上書きコピー）
- Modify: `C:\Users\PC_User\Documents\vrc-mascot-pwa\model.usdz`（上書きコピー）
- Modify: `C:\Users\PC_User\Documents\vrc-mascot-pwa\sw.js`（CACHE_VERSIONを上げる）

- [ ] **Step 1: `ar-avatar-demo`をpushし、公開サイトの反映を確認する**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git push
curl -s -o /dev/null -w "%{http_code}\n" https://hasegawakasyouen.github.io/ar-avatar-demo/model.glb
```

- [ ] **Step 2: `vrc-mascot-pwa`にモデルをコピーする**

```bash
cp "C:\Users\PC_User\Documents\ar-avatar-demo\model.glb" "C:\Users\PC_User\Documents\vrc-mascot-pwa\model.glb"
cp "C:\Users\PC_User\Documents\ar-avatar-demo\model.usdz" "C:\Users\PC_User\Documents\vrc-mascot-pwa\model.usdz"
```

- [ ] **Step 3: `sw.js`の`CACHE_VERSION`を上げる**

`sw.js`冒頭の`CACHE_VERSION`を`'mascot-cache-v3'`に変更する（現在`'mascot-cache-v2'`のはず。実際の現在値を確認してから、次の番号に上げること）。

- [ ] **Step 4: コミット・push**

```bash
cd "C:\Users\PC_User\Documents\vrc-mascot-pwa"
git add model.glb model.usdz sw.js
git commit -m "asset: apply restored accent material values, bump cache version"
git push
```

- [ ] **Step 5: 公開サイトの反映を確認する**

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://hasegawakasyouen.github.io/vrc-mascot-pwa/model.glb
```

---

### Task 5: iPhone実機で確認する（手動）

**Files:** なし

- [ ] **Step 1: `ar-avatar-demo`の公開URLをiPhoneのSafariで開く**

`https://hasegawakasyouen.github.io/ar-avatar-demo/` を開き、見た目に問題がないか（テクスチャが正しく表示され、崩れがないか）確認する。

- [ ] **Step 2: `vrc-mascot-pwa`をiPhoneで開く**

タップでアニメーション切り替え・バウンド演出・AR起動が引き続き問題ないことを確認する。

- [ ] **Step 3: 問題があれば記録**

---

## Self-Review メモ

- **Spec網羅性**: design specの各要素（metal追加/Diamond・pearl/chain/tear/動作確認）に対応するTaskをすべて用意した
- **プレースホルダ**: 「TBD」「後で」は含まない。Principled BSDFの入力ソケット名のみ実行時検証が必要な旨を明記しているが、これは具体的な確認手順を伴う指示
- **型/名称の一貫性**: `MATERIAL_TEXTURE_MAP`・`tune_material_pbr_values()`の呼び出し順序（`relink_material_textures()`の後）はTask 1・Task 2で一貫している
- **既存機能への影響**: `Gam`・`Maid`・アニメーション合成・他6テクスチャには一切触れないため、回帰確認をTask 3に明記した
