# 「りりか 黒猫悪夢」VRM化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unity/VRChat用に改変済みの別アバター「りりか 黒猫悪夢」をVRM 1.0形式に変換し、[[project-desktop-vrm-mascot]]で選択して使えるようにする。

**Architecture:** 既存の`export_vrm.py`と同じ構造（`BONE_MAPPING`・`PRESET_EXPRESSION_MAPPING`・`CUSTOM_EXPRESSION_MAPPING`・VRM Add-on呼び出し）を踏襲しつつ、入力元をFBX（`ririka 黒猫悪夢(Clone).fbx`）専用の新規スクリプト群として作る。既存の`export_vrm.py`/`export_vrma.py`はリリカ本体・アニメーションパイプライン用のため一切変更しない。

**Tech Stack:** Blender 4.5 headless（`bpy`）、VRM Add-on for Blender、Node.js（VRM構造検証用）、`ar-avatar-demo/vrm-preview.html`（three-vrmブラウザ検証）

**設計書:** `docs/superpowers/specs/2026-07-12-ririka-kaihen-vrm-export-design.md`

**この計画作成前に判明した事実（設計書のフォローアップ調査、実装前に確定済み）:**
- 視素(`vrc.v_aa`等)・`nagomi`(relaxed)・`びっくり`(surprised)のシェイプキーは全て存在を確認済み。プリセット表情マッピングは元の`export_vrm.py`と全く同じ構成でよい
- Hipsボーン問題の原因を特定済み: Armatureオブジェクト自体のワールド座標Z=0.7251m（想定される腰の高さと一致）が、本来「Hips」ボーンが担うべき位置を担っている。`Spine`/`Upperleg_L`/`Upperleg_R`はいずれも`parent=None`でこのArmatureのローカル原点(0,0,0)を基準に配置されている。解決策: Armatureのローカル原点(0,0,0)に新規`Hips`ボーンを1本追加し、`Spine`・`Upperleg_L`・`Upperleg_R`をその子としてペアレントし直す

---

### Task 1: Hipsボーンを追加した作業用.blendファイルを作成する

**Files:**
- Create: `ar-avatar-demo/scripts/prepare_ririka_kaihen_blend.py`
- Create (実行結果、gitコミット対象外): `ar-avatar-demo/source/ririka_kaihen.blend`

- [ ] **Step 1: スクリプトを作成する**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""「りりか 黒猫悪夢」のFBXをインポートし、単体で存在しないHipsボーンを
Armatureオブジェクトのローカル原点（実測でワールドZ=0.7251m、想定される腰の高さと一致）に
新規追加してSpine/Upperleg_L/Upperleg_Rを再ペアレントしたうえで、
作業用.blendとして保存する。元のFBX/Unityプロジェクトは一切変更しない。
"""
import sys
import bpy

ARMATURE_NAME = "Hips"
HUMANOID_CHAIN_ROOTS = ["Spine", "Upperleg_L", "Upperleg_R"]


def get_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python prepare_ririka_kaihen_blend.py "
            "-- <source_fbx> <output_blend>"
        )
    return argv[argv.index("--") + 1:]


def parse_args(args):
    if len(args) != 2:
        raise SystemExit("Expected 2 positional args: <source_fbx> <output_blend>")
    return args[0], args[1]


def add_hips_bone(armature_object):
    bpy.context.view_layer.objects.active = armature_object
    armature_object.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = armature_object.data.edit_bones

    if "Hips" in edit_bones:
        raise RuntimeError("すでに'Hips'という名前のボーンが存在します。想定外の状態です")

    hips_bone = edit_bones.new("Hips")
    hips_bone.head = (0.0, 0.0, 0.0)
    hips_bone.tail = (0.0, 3.0, 0.0)
    hips_bone.roll = 0.0

    missing = []
    for name in HUMANOID_CHAIN_ROOTS:
        b = edit_bones.get(name)
        if b is None:
            missing.append(name)
            continue
        b.parent = hips_bone
        b.use_connect = False

    bpy.ops.object.mode_set(mode='OBJECT')

    if missing:
        raise RuntimeError(f"以下のボーンが見つかりません: {missing}")


if __name__ == "__main__":
    source_fbx, output_blend = parse_args(get_args())

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=source_fbx)

    armature_object = bpy.data.objects.get(ARMATURE_NAME)
    if armature_object is None or armature_object.type != 'ARMATURE':
        raise RuntimeError(f"Armatureオブジェクト'{ARMATURE_NAME}'が見つかりません")

    add_hips_bone(armature_object)
    print("HIPS_BONE_ADDED")

    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    print(f"SAVED: {output_blend}")
```

- [ ] **Step 2: 実行する**

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python "C:\Users\PC_User\Documents\ar-avatar-demo\scripts\prepare_ririka_kaihen_blend.py" -- "D:\VRChatCreatorCompanion\VRChatProjects\りりか　黒猫悪夢\Assets\ririka 黒猫悪夢(Clone).fbx" "C:\Users\PC_User\Documents\ar-avatar-demo\source\ririka_kaihen.blend"
```

Expected: 標準出力に`HIPS_BONE_ADDED`、続けて`SAVED: ...\ririka_kaihen.blend`が出力される。エラーなく終了すること。

- [ ] **Step 3: 新しいHipsボーンの位置を目視確認するレンダリングを行う**

```python
# ar-avatar-demo/scripts/_verify_hips_render.py (使い捨て確認用、コミット不要)
import bpy
import math

bpy.ops.wm.open_mainfile(filepath=r"C:\Users\PC_User\Documents\ar-avatar-demo\source\ririka_kaihen.blend")

scene = bpy.context.scene
armature = bpy.data.objects["Hips"]
armature.data.pose_position = 'REST'

# Hipsボーンをオレンジ色の小さい球で可視化する
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03, location=(0, 0, 0.7251))
marker = bpy.context.active_object
marker.name = "HipsMarker"
mat = bpy.data.materials.new("HipsMarkerMat")
mat.diffuse_color = (1.0, 0.4, 0.0, 1.0)
marker.data.materials.append(mat)

cam_data = bpy.data.cameras.new("VerifyCam")
cam_obj = bpy.data.objects.new("VerifyCam", cam_data)
scene.collection.objects.link(cam_obj)
cam_obj.location = (0, -3.0, 0.9)
cam_obj.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam_obj

light_data = bpy.data.lights.new("VerifyLight", type='SUN')
light_obj = bpy.data.objects.new("VerifyLight", light_data)
scene.collection.objects.link(light_obj)
light_obj.rotation_euler = (math.radians(45), 0, math.radians(45))

scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 500
scene.render.resolution_y = 700
scene.render.filepath = r"C:\Users\PC_User\AppData\Local\Temp\claude\C--Users-PC-User--claude\531d5ae0-b953-47d1-b003-b1d7f8c26c34\scratchpad\hips_verify.png"
scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
print("RENDER_DONE")
```

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python "C:\Users\PC_User\Documents\ar-avatar-demo\scripts\_verify_hips_render.py"
```

生成された`hips_verify.png`をReadツールで開き、オレンジ色のマーカーがキャラクターの腰（股の少し上、骨盤の高さ）に位置しているかを目視確認する。明らかに胸の高さや膝の高さなど不自然な位置にある場合は、Step 1のマーカー座標`(0, 0, 0.7251)`が誤りなので、Armatureのワールド座標を再計測して修正する。

- [ ] **Step 4: 確認用の一時ファイルを削除する**

`ar-avatar-demo/scripts/_verify_hips_render.py`を削除する（確認用の使い捨てスクリプトのため、コミットしない）。

- [ ] **Step 5: commit**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add scripts/prepare_ririka_kaihen_blend.py
git commit -m "feat: 「りりか 黒猫悪夢」用にHipsボーンを補完する前処理スクリプトを追加"
```

---

### Task 2: VRM出力スクリプトを作成し実行する

**Files:**
- Create: `ar-avatar-demo/scripts/export_vrm_ririka_kaihen.py`
- Create (実行結果、gitコミット対象外): `ar-avatar-demo/ririka_kaihen.vrm`

- [ ] **Step 1: スクリプトを作成する**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ririka_kaihen.blend（Task 1で作成、Hipsボーン補完済み）からVRM 1.0形式で
ririka_kaihen.vrmを出力する。元の.blendファイルは一切変更しない。
"""
import sys
import bpy

ARMATURE_NAME = "Hips"
BODY_MESH_NAME = "Body"

PRESET_EXPRESSION_MAPPING = {
    "happy": (BODY_MESH_NAME, "happy"),
    "angry": (BODY_MESH_NAME, "angry"),
    "sad": (BODY_MESH_NAME, "sad"),
    "relaxed": (BODY_MESH_NAME, "nagomi"),
    "surprised": (BODY_MESH_NAME, "びっくり"),
    "aa": (BODY_MESH_NAME, "vrc.v_aa"),
    "ih": (BODY_MESH_NAME, "vrc.v_ih"),
    "ou": (BODY_MESH_NAME, "vrc.v_ou"),
    "ee": (BODY_MESH_NAME, "vrc.v_e"),
    "oh": (BODY_MESH_NAME, "vrc.v_oh"),
    "blink": (BODY_MESH_NAME, "blink"),
    "blink_left": (BODY_MESH_NAME, "blink_L"),
    "blink_right": (BODY_MESH_NAME, "blink_R"),
}

CUSTOM_EXPRESSION_MAPPING = {
    "crying": [
        (BODY_MESH_NAME, "sad"),
        (BODY_MESH_NAME, "tear1"),
        (BODY_MESH_NAME, "tear2"),
    ],
    "joy": [
        (BODY_MESH_NAME, "joy"),
        (BODY_MESH_NAME, "joy2"),
        (BODY_MESH_NAME, "brow_joy"),
    ],
}

# VRM Humanoidボーン名 -> 「りりか 黒猫悪夢」側のボーン名
# 手のボーンのみ元のririka_v1.0.9と表記が異なる（アンダースコア区切り）。
# 親指のみVRM側がmetacarpal/proximal/distalの3段階なのに対しこのアバターも
# Proximal/Intermediate/Distalの3段階（意味が1段階ズレる）ため、
# 元のBONE_MAPPINGと同様に1段階前へずらしてマッピングする
BONE_MAPPING = {
    "hips": "Hips",
    "spine": "Spine",
    "chest": "Chest",
    "neck": "Neck",
    "head": "Head",
    "left_eye": "eye_L",
    "right_eye": "eye_R",
    "left_shoulder": "sholder_L",
    "right_shoulder": "sholder_R",
    "left_upper_arm": "Upperarm_L",
    "right_upper_arm": "Upperarm_R",
    "left_lower_arm": "Lowerarm_L",
    "right_lower_arm": "Lowerarm_R",
    "left_hand": "Left_Hand",
    "right_hand": "Right_Hand",
    "left_upper_leg": "Upperleg_L",
    "right_upper_leg": "Upperleg_R",
    "left_lower_leg": "Lowerleg_L",
    "right_lower_leg": "Lowerleg_R",
    "left_foot": "Foot_L",
    "right_foot": "Foot_R",
    "left_toes": "Toe_L",
    "right_toes": "Toe_R",
    "left_thumb_metacarpal": "Thumb Proximal_L",
    "left_thumb_proximal": "Thumb Intermediate_L",
    "left_thumb_distal": "Thumb Distal_L",
    "right_thumb_metacarpal": "Thumb Proximal_R",
    "right_thumb_proximal": "Thumb Intermediate_R",
    "right_thumb_distal": "Thumb Distal_R",
    "left_index_proximal": "Index Proximal_L",
    "left_index_intermediate": "Index Intermediate_L",
    "left_index_distal": "Index Distal_L",
    "right_index_proximal": "Index Proximal_R",
    "right_index_intermediate": "Index Intermediate_R",
    "right_index_distal": "Index Distal_R",
    "left_middle_proximal": "Middle Proximal_L",
    "left_middle_intermediate": "Middle Intermediate_L",
    "left_middle_distal": "Middle Distal_L",
    "right_middle_proximal": "Middle Proximal_R",
    "right_middle_intermediate": "Middle Intermediate_R",
    "right_middle_distal": "Middle Distal_R",
    "left_ring_proximal": "Ring Proximal_L",
    "left_ring_intermediate": "Ring Intermediate_L",
    "left_ring_distal": "Ring Distal_L",
    "right_ring_proximal": "Ring Proximal_R",
    "right_ring_intermediate": "Ring Intermediate_R",
    "right_ring_distal": "Ring Distal_R",
    "left_little_proximal": "Little Proximal_L",
    "left_little_intermediate": "Little Intermediate_L",
    "left_little_distal": "Little Distal_L",
    "right_little_proximal": "Little Proximal_R",
    "right_little_intermediate": "Little Intermediate_R",
    "right_little_distal": "Little Distal_R",
}


def get_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python export_vrm_ririka_kaihen.py "
            "-- <source_blend> <output_vrm>"
        )
    return argv[argv.index("--") + 1:]


def parse_args(args):
    if len(args) != 2:
        raise SystemExit("Expected 2 positional args: <source_blend> <output_vrm>")
    return args[0], args[1]


def get_armature_object():
    obj = bpy.data.objects.get(ARMATURE_NAME)
    if obj is None or obj.type != 'ARMATURE':
        raise RuntimeError(f"Armatureオブジェクト'{ARMATURE_NAME}'が見つかりません")
    return obj


def apply_bone_mapping(armature_object):
    ext = armature_object.data.vrm_addon_extension
    ext.spec_version = "1.0"
    human_bones = ext.vrm1.humanoid.human_bones
    missing = []
    for vrm_bone_name, source_bone_name in BONE_MAPPING.items():
        if source_bone_name not in armature_object.data.bones:
            missing.append((vrm_bone_name, source_bone_name))
            continue
        human_bone = getattr(human_bones, vrm_bone_name)
        human_bone.node.bone_name = source_bone_name
    if missing:
        raise RuntimeError(f"以下のボーンが見つかりません: {missing}")


def _add_morph_target_bind(expression, mesh_name, shape_key_name):
    mesh_object = bpy.data.objects.get(mesh_name)
    if mesh_object is None or mesh_object.type != 'MESH':
        raise RuntimeError(f"メッシュオブジェクト'{mesh_name}'が見つかりません")
    if mesh_object.data.shape_keys is None or shape_key_name not in mesh_object.data.shape_keys.key_blocks:
        raise RuntimeError(f"'{mesh_name}'にシェイプキー'{shape_key_name}'が見つかりません")
    bind = expression.morph_target_binds.add()
    bind.node.mesh_object_name = mesh_name
    bind.index = shape_key_name
    bind.weight = 1.0


def apply_expression_mapping(armature_object):
    expressions = armature_object.data.vrm_addon_extension.vrm1.expressions

    for preset_name, (mesh_name, shape_key_name) in PRESET_EXPRESSION_MAPPING.items():
        expression = getattr(expressions.preset, preset_name)
        _add_morph_target_bind(expression, mesh_name, shape_key_name)

    for custom_name, binds in CUSTOM_EXPRESSION_MAPPING.items():
        custom_expression = expressions.custom.add()
        custom_expression.custom_name = custom_name
        for mesh_name, shape_key_name in binds:
            _add_morph_target_bind(custom_expression, mesh_name, shape_key_name)


def apply_meta(armature_object):
    meta = armature_object.data.vrm_addon_extension.vrm1.meta
    meta.vrm_name = "Ririka Kaihen (dev export)"
    meta.version = "0.0.1-dev"
    author = meta.authors.add()
    author.value = "hasegawakasyouen (dev/internal use only)"
    meta.avatar_permission = "onlyAuthor"
    meta.commercial_usage = "personalNonProfit"
    meta.modification = "prohibited"


if __name__ == "__main__":
    source_blend, output_vrm = parse_args(get_args())

    bpy.ops.wm.open_mainfile(filepath=source_blend)
    armature_object = get_armature_object()
    apply_bone_mapping(armature_object)
    apply_expression_mapping(armature_object)
    apply_meta(armature_object)
    print("MAPPING_DONE")

    result = bpy.ops.export_scene.vrm(
        filepath=output_vrm,
        armature_object_name=ARMATURE_NAME,
        ignore_warning=True,
        enable_advanced_preferences=True,
        export_try_sparse_sk=True,
    )
    print(f"EXPORT_RESULT: {result}")
    if result != {'FINISHED'}:
        raise RuntimeError(f"VRMエクスポートが失敗しました: {result}")
```

- [ ] **Step 2: 実行する**

```bash
"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --python "C:\Users\PC_User\Documents\ar-avatar-demo\scripts\export_vrm_ririka_kaihen.py" -- "C:\Users\PC_User\Documents\ar-avatar-demo\source\ririka_kaihen.blend" "C:\Users\PC_User\Documents\ar-avatar-demo\ririka_kaihen.vrm"
```

（VRM Add-onはBlender 5.1にインストール済みのため、Task 1と違いこのステップはBlender 5.1で実行する）

Expected: 標準出力に`MAPPING_DONE`、続けて`EXPORT_RESULT: {'FINISHED'}`が出力される。`RuntimeError`が出た場合は、メッセージに含まれるボーン名/シェイプキー名を確認し、Task 1で実際に確認したボーン一覧・本タスクのシェイプキー一覧と照合する。

- [ ] **Step 3: commit**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add scripts/export_vrm_ririka_kaihen.py
git commit -m "feat: 「りりか 黒猫悪夢」用のVRM出力スクリプトを追加"
```

---

### Task 3: 表情の見た目を確認し必要ならweightを調整する

**Files:**
- Modify: `ar-avatar-demo/scripts/export_vrm_ririka_kaihen.py`（見た目に問題があった場合のみ）

- [ ] **Step 1: 各表情のレンダリング画像を生成して比較する**

```python
# ar-avatar-demo/scripts/_verify_expressions_render.py (使い捨て確認用、コミット不要)
import bpy
import math

bpy.ops.wm.open_mainfile(filepath=r"C:\Users\PC_User\Documents\ar-avatar-demo\source\ririka_kaihen.blend")

body = bpy.data.objects["Body"]
key_blocks = body.data.shape_keys.key_blocks

scene = bpy.context.scene
cam_data = bpy.data.cameras.new("ExprCam")
cam_obj = bpy.data.objects.new("ExprCam", cam_data)
scene.collection.objects.link(cam_obj)
cam_obj.location = (0, -1.2, 1.55)
cam_obj.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam_obj

light_data = bpy.data.lights.new("ExprLight", type='SUN')
light_obj = bpy.data.objects.new("ExprLight", light_data)
scene.collection.objects.link(light_obj)
light_obj.rotation_euler = (math.radians(45), 0, math.radians(45))

scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 500
scene.render.resolution_y = 500
scene.render.image_settings.file_format = 'PNG'

expressions_to_check = {
    "happy": ["happy", "brow_smile", "mouth_smile"],
    "angry": ["angry", "brow_angry"],
    "sad": ["sad", "mouth_sad"],
    "crying": ["sad", "tear1", "tear2"],
    "joy": ["joy", "joy2", "brow_joy"],
}

for expr_name, shape_key_names in expressions_to_check.items():
    for kb in key_blocks:
        kb.value = 0.0
    for name in shape_key_names:
        if name in key_blocks:
            key_blocks[name].value = 1.0
        else:
            print(f"WARNING: shape key '{name}' not found for expression '{expr_name}'")
    scene.render.filepath = f"C:\\Users\\PC_User\\AppData\\Local\\Temp\\claude\\C--Users-PC-User--claude\\531d5ae0-b953-47d1-b003-b1d7f8c26c34\\scratchpad\\expr_{expr_name}.png"
    bpy.ops.render.render(write_still=True)
    print(f"RENDERED: {expr_name}")
```

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python "C:\Users\PC_User\Documents\ar-avatar-demo\scripts\_verify_expressions_render.py"
```

生成された`expr_happy.png`・`expr_angry.png`・`expr_sad.png`・`expr_crying.png`・`expr_joy.png`をReadツールで1枚ずつ確認する。

- [ ] **Step 2: 見た目に問題があれば調整する**

以下のいずれかに該当する場合、`export_vrm_ririka_kaihen.py`の該当する`PRESET_EXPRESSION_MAPPING`/`CUSTOM_EXPRESSION_MAPPING`のシェイプキー構成を調整し、Task 2のStep 2を再実行して確認し直す。

- 表情が薄すぎて無表情に見える場合: 構成するシェイプキーを追加する、または`_add_morph_target_bind`の`weight`を1.0のまま複数キー分重ねる
- 表情が誇張されすぎて不自然な場合: 構成するシェイプキーを減らす
- `happy`と`joy`の区別がつかないほど似ている場合: どちらかの構成シェイプキーを調整して差別化する（例: `joy`側は`joy2`の比重を強める）

問題がなければこのステップはスキップしてよい。

- [ ] **Step 3: 確認用の一時ファイルを削除する**

`ar-avatar-demo/scripts/_verify_expressions_render.py`を削除する（コミットしない）。

- [ ] **Step 4: commit（Step 2で調整した場合のみ）**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add scripts/export_vrm_ririka_kaihen.py
git commit -m "fix: 表情の見た目確認結果を反映してシェイプキー構成を調整"
```

---

### Task 4: three-vrmブラウザプレビューで動作確認する

**Files:** なし（動作確認のみ）

- [ ] **Step 1: `vrm-preview.html`で読み込み確認する**

```bash
cp "C:\Users\PC_User\Documents\ar-avatar-demo\ririka_kaihen.vrm" "C:\Users\PC_User\Documents\ar-avatar-demo\model_kaihen_verify.vrm"
```

`ar-avatar-demo/vrm-preview.html`の`vrmLoader.load('model.vrm', ...)`を一時的に`vrmLoader.load('model_kaihen_verify.vrm', ...)`に書き換える。

```
mcp__Claude_Browser__preview_start { name: "ar-avatar-demo" }
```

でサーバーを起動し、`http://localhost:8080/vrm-preview.html`を開く。コンソールに`VRM_LOADED`が出力され、キャラクターがTポーズ等で正しく表示されることを確認する。崩れたメッシュ・透明になったパーツ・極端に歪んだ形状がないか目視確認する。

- [ ] **Step 2: 一時変更を元に戻す**

`vrm-preview.html`の書き換えを`vrmLoader.load('model.vrm', ...)`に戻す。`model_kaihen_verify.vrm`を削除する。

---

### Task 5: デスクトップアプリでの最終動作確認

**Files:** なし（動作確認のみ）

- [ ] **Step 1: VRMファイルをデスクトップアプリから選択できる場所に置く**

```bash
cp "C:\Users\PC_User\Documents\ar-avatar-demo\ririka_kaihen.vrm" "C:\Users\PC_User\Documents\desktop-vrm-mascot\assets\dev-avatars\ririka_kaihen.vrm"
```

（`desktop-vrm-mascot/assets/dev-avatars/`ディレクトリが無ければ作成する。このファイルはVRMファイル選択ダイアログから手動で選ぶための開発用配置であり、`assets/animations/`とは異なりコミット対象外）

- [ ] **Step 2: デスクトップアプリを起動しVRMを切り替える**

```bash
cd "C:\Users\PC_User\Documents\desktop-vrm-mascot"
npm start
```

タスクトレイの「VRMを選択」から`ririka_kaihen.vrm`を選ぶ。

- [ ] **Step 3: 一連の動作を確認する**

1. VRMが正しく読み込まれ、待機中は食事モーションがループすることを確認する
2. しばらく待って徘徊状態(歩行モーション)に遷移することを確認する
3. キャラをクリックして喜ぶモーション+happy表情が発火することを確認する
4. `Math.random`を固定するデバッグ手法（このプロジェクトで確立済み）を使い、壁衝突による泣きモーション+crying表情を強制発火させ、正しく動作することを確認する
5. Humanoidボーンマッピングが不完全な場合にモーションが破綻していないか（手足が変な方向に伸びる等）を目視確認する

- [ ] **Step 4: 問題があれば記録する**

モーションや表情に不自然な破綻があった場合、どのボーン/シェイプキーに起因するか特定できる範囲でメモしておく（Task 2のBONE_MAPPING・Task 3の表情マッピングの再調整が必要になる可能性がある）。

- [ ] **Step 5: アプリを終了する**

タスクトレイの「終了」、またはプロセスを直接終了する。
