# 顔UV結合バグ・髪テクスチャ端ラップ修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** アバターの顔に目・口・眉などの表情要素を表示させ、髪の黒い帯状のテクスチャ乱れを解消する。

**Architecture:** `prepare_for_mixamo.py`のメッシュ結合前にUVレイヤー名を統一する処理を追加し、`convert_to_web.py`のテクスチャノードの拡張モードを`EXTEND`に変更する。

**Tech Stack:** Blender 4.5（bpy headless script）、Mixamo（web、手動操作）

**確認済みの環境:**
- `Body`メッシュ（顔）の実UVデータは`'UVMap'`レイヤーにあるが、結合の基準になる`Bag`メッシュのアクティブレイヤーは`'UVマップ'`のため、結合後は`Body`の顔UVが失われ座標(0,0)になる
- `Hair.png`の下端はほぼ純黒（RGB平均 0.3, 0.5, 0.4）。`Hair`マテリアルのUV座標は`v=-0.0108`など0〜1をわずかに超えており、デフォルトの`REPEAT`拡張モードだとこの黒い端を巻き込む

---

### Task 1: `prepare_for_mixamo.py`にUVレイヤー統一処理を追加する

**Files:**
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\scripts\prepare_for_mixamo.py`

- [ ] **Step 1: `normalize_active_uv_layer()`関数を追加する**

`join_meshes()`関数の直前に、以下の関数を追加する:

```python
def normalize_active_uv_layer(mesh_objs, target_name="UVMap"):
    for obj in mesh_objs:
        uv_layers = obj.data.uv_layers
        active = uv_layers.active
        if active is None:
            continue
        if active.name == target_name:
            continue
        existing = uv_layers.get(target_name)
        if existing is not None:
            existing.name = target_name + "_orig"
        active.name = target_name
```

- [ ] **Step 2: `main()`内で`join_meshes()`の直前に呼び出す**

`main()`関数内の以下の箇所:

```python
    remove_shape_keys(mesh_objs)
    joined = join_meshes(mesh_objs)
```

を、以下のように書き換える:

```python
    remove_shape_keys(mesh_objs)
    normalize_active_uv_layer(mesh_objs)
    joined = join_meshes(mesh_objs)
```

- [ ] **Step 3: 実データでUV統一を検証する**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\prepare_for_mixamo.py -- "D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\FBX\ririka.fbx" "C:\Users\PC_User\AppData\Local\Temp\claude\prepare_uvtest.fbx" --decimate-threshold 200000
```

Expected: `PREPARE_OK`

以下の内容で一時ファイル`C:\Users\PC_User\AppData\Local\Temp\claude\verify_uv.py`を作成する:

```python
import bpy, sys
argv = sys.argv[sys.argv.index("--") + 1:]
fbx_path = argv[0]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx_path)
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
obj = mesh_objs[0]
mesh = obj.data
slot_names = [s.material.name if s.material else None for s in obj.material_slots]
uv_layer = mesh.uv_layers.active
print("active uv layer:", uv_layer.name)
for target in ("body", "Gam", "tear", "Hair"):
    if target not in slot_names:
        print(target, "NOT IN SLOTS")
        continue
    idx = slot_names.index(target)
    us, vs = [], []
    for p in mesh.polygons:
        if p.material_index == idx:
            for li in p.loop_indices:
                uv = uv_layer.data[li].uv
                us.append(uv.x); vs.append(uv.y)
    print(f"{target}: UV range u=({min(us):.4f},{max(us):.4f}) v=({min(vs):.4f},{max(vs):.4f})")
```

実行する:

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python "C:\Users\PC_User\AppData\Local\Temp\claude\verify_uv.py" -- "C:\Users\PC_User\AppData\Local\Temp\claude\prepare_uvtest.fbx"
```

Expected: `body`・`Gam`・`tear`のUV範囲がいずれも`(0.0000,0.0000)`ではなく、0〜1の範囲内に妥当に分布していること（`body`はおおよそ`u=(0.00,1.00) v=(0.00,1.00)`程度の広い範囲）。

- [ ] **Step 4: 一時ファイルを削除する**

```bash
rm -f "C:\Users\PC_User\AppData\Local\Temp\claude\prepare_uvtest.fbx" "C:\Users\PC_User\AppData\Local\Temp\claude\verify_uv.py"
```

- [ ] **Step 5: コミット**

```bash
git add scripts/prepare_for_mixamo.py
git commit -m "fix: normalize active UV layer name before joining meshes to prevent face UV data loss"
```

---

### Task 2: `convert_to_web.py`のテクスチャ拡張モードを`EXTEND`にする

**Files:**
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\scripts\convert_to_web.py`

- [ ] **Step 1: `relink_material_textures()`内のテクスチャノード生成箇所を修正する**

`scripts/convert_to_web.py`の`relink_material_textures()`関数内、以下の箇所:

```python
        tex_node = node_tree.nodes.new("ShaderNodeTexImage")
        tex_node.image = image
        node_tree.links.new(tex_node.outputs["Color"], base_color_input)
```

を、以下のように書き換える:

```python
        tex_node = node_tree.nodes.new("ShaderNodeTexImage")
        tex_node.image = image
        tex_node.extension = 'EXTEND'
        node_tree.links.new(tex_node.outputs["Color"], base_color_input)
```

- [ ] **Step 2: スモークテストで後方互換性を確認する**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\convert_to_web.py -- --smoketest smoketest.glb smoketest.usdz
```

Expected: `CONVERT_OK smoketest.glb smoketest.usdz`、終了コード0（デフォルトCubeシーンには対象マテリアルが存在しないため、この変更で壊れないはず）。確認後、生成ファイルは削除してよい。

- [ ] **Step 3: コミット**

```bash
git add scripts/convert_to_web.py
git commit -m "fix: use EXTEND texture wrap mode to prevent UV-out-of-range wraparound artifacts"
```

---

### Task 3: フル品質版FBXを再生成し、Mixamoへ再アップロードする（手動ステップ含む）

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_full_for_mixamo.fbx`（一時ファイル）
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_idle_mixamo.fbx`
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_wave_mixamo.fbx`
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_dance_mixamo.fbx`

- [ ] **Step 1: 修正済みスクリプトでフル品質版FBXを生成する**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\prepare_for_mixamo.py -- "D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\FBX\ririka.fbx" source\avatar_full_for_mixamo.fbx --decimate-threshold 200000
```

Expected: `PREPARE_INFO triangles=166702 <= threshold=200000, skipping decimate`、`PREPARE_OK`

（`source/avatar_full_for_mixamo.fbx`は既に`.gitignore`に登録済みのため、コミット不要）

- [ ] **Step 2: Mixamoへアップロードしてオートリギングを実行する（手動）**

以前と同じ手順（[Mesh] Task 3で確立済み）。`https://www.mixamo.com/`に`source\avatar_full_for_mixamo.fbx`をアップロードし、オートリギング後にidle・wave・danceの3アニメーションをFBXでダウンロードする。

- [ ] **Step 3: ダウンロードした3ファイルで`source\`内の既存ファイルを置き換える（手動）**

```
avatar_idle_mixamo.fbx
avatar_wave_mixamo.fbx
avatar_dance_mixamo.fbx
```

置き換え完了をこの会話で報告する。

- [ ] **Step 4: コミット**

```bash
git add source/avatar_idle_mixamo.fbx source/avatar_wave_mixamo.fbx source/avatar_dance_mixamo.fbx
git commit -m "asset: re-rig with UV-layer-normalized mesh to fix face/hair texture mapping"
```

---

### Task 4: 実データで再変換・検証する

**Files:**
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\model.glb`
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\model.usdz`

- [ ] **Step 1: 変換を実行する**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\convert_to_web.py -- source\avatar_idle_mixamo.fbx model.glb model.usdz source\avatar_wave_mixamo.fbx source\avatar_dance_mixamo.fbx
```

Expected: `CONVERT_OK model.glb model.usdz`

- [ ] **Step 2: GLBのJSONを解析し、UV修正を検証する**

`body`・`Gam`・`tear`マテリアルの`baseColorTexture`参照先画像が存在し、`accessors`内の対応するUV座標のmin/maxが`(0,0)`固定になっていないことを確認する。`Hair`マテリアルのテクスチャの`samplers`内`wrapS`/`wrapT`が`33071`（CLAMP_TO_EDGE）になっていることを確認する（`10497`のREPEATのままなら`extension = 'EXTEND'`が反映されていない）。

- [ ] **Step 3: ブラウザプレビューで目視確認する**

ローカルサーバーで`model.glb`を表示し、顔をズームしたスクリーンショットを撮る。目・眉・口などの表情要素が表示されていることを確認する。後頭部もズームし、黒い帯状の乱れが解消されている（または大幅に改善している）ことを確認する。改善が不十分な場合はこの会話で報告し、追加調査する。

- [ ] **Step 4: 既存機能への回帰がないことを確認する**

3アニメーション・スキン・`metal`/`Diamond`/`pearl`/`chain`/`tear`の各マテリアル値が[Mesh]・[Accent]作業時の値のまま維持されていることを確認する。

- [ ] **Step 5: コミット**

```bash
git add model.glb model.usdz
git commit -m "asset: regenerate model.glb/usdz with fixed face UV and hair texture wrap"
```

---

### Task 5: 両プロジェクトへデプロイする

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

`sw.js`冒頭の`CACHE_VERSION`を確認し、次の番号に上げる（現在`'mascot-cache-v5'`のはずなので`'mascot-cache-v6'`にする。実際の現在値を確認してから次の番号にすること）。

- [ ] **Step 4: コミット・push**

```bash
cd "C:\Users\PC_User\Documents\vrc-mascot-pwa"
git add model.glb model.usdz sw.js
git commit -m "asset: apply fixed face/hair texture mapping, bump cache version"
git push
```

- [ ] **Step 5: 公開サイトの反映を確認する**

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://hasegawakasyouen.github.io/vrc-mascot-pwa/model.glb
```

---

### Task 6: iPhone実機で確認する（手動）

**Files:** なし

- [ ] **Step 1: `ar-avatar-demo`の公開URLをiPhoneのSafariで開く**

`https://hasegawakasyouen.github.io/ar-avatar-demo/` を開き、顔に目・口・眉が表示されていること、髪の黒い乱れが解消されていることを確認する。

- [ ] **Step 2: `vrc-mascot-pwa`をiPhoneで開く**

同様の見た目確認に加え、タップでのアニメーション切り替え・AR起動が引き続き問題ないことを確認する。

- [ ] **Step 3: 問題があれば記録**

---

## Self-Review メモ

- **Spec網羅性**: design specの2つの原因（顔UV結合バグ・髪テクスチャ端ラップ）に対応する修正（Task 1・Task 2）と、検証・デプロイ・実機確認（Task 3〜6）をすべて用意した
- **プレースホルダ**: 「TBD」「後で」は含まない
- **型/名称の一貫性**: `normalize_active_uv_layer(mesh_objs, target_name="UVMap")`はTask 1内で完結。`tex_node.extension = 'EXTEND'`はTask 2内で完結。他タスクからの直接呼び出しはない
- **既存機能への影響**: `decimate_if_needed()`・`strip_armature()`・`tune_material_pbr_values()`・アニメーション合成には触れないため、Task 4のStep 4で回帰確認を明記した
