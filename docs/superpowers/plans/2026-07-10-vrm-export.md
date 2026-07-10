# リリカアバターのVRM化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `ririka.blend`から、VRM 1.0形式の`model.vrm`を出力できるようにする。既存のBlender→Mixamo→GLB/USDZパイプラインとは別の出力経路として追加する。

**Architecture:** VRM Add-on for Blender（`saturday06/VRM-Addon-for-Blender`、Blender公式拡張機能プラットフォームにも掲載）をBlender 4.5にインストールし、そのPython API（`armature.data.vrm_addon_extension`）をheadlessスクリプトから直接操作してHumanoidボーンマッピング・表情マッピングを設定し、`bpy.ops.export_scene.vrm()`でエクスポートする。GUIでのクリック操作は一切行わない（このBlender環境にはディスプレイが無いため）。

**Tech Stack:** Blender 4.5.2 LTS（headless）、VRM Add-on for Blender v4.3.3、`@pixiv/three-vrm`（検証用ビューアー、CDN経由）。

---

## 前提として確認済みの事実

VRM Add-onの実際のソースコード（GitHub上の公開リポジトリ、タグ`v4.3.3`）を読んで確認済み（推測ではない）:

- ボーンマッピングのプロパティパスは `armature_object.data.vrm_addon_extension.vrm1.humanoid.human_bones.<bone_name>.node.bone_name`（例: `.hips.node.bone_name = "Hips"`）
- 表情プリセットのプロパティパスは `armature_object.data.vrm_addon_extension.vrm1.expressions.preset.<preset_name>`、各プリセットは`Vrm1ExpressionPropertyGroup`型で、`.morph_target_binds`（コレクション）に`.node.mesh_object_name`（文字列、メッシュオブジェクト名）・`.index`（文字列、シェイプキー名）・`.weight`（0〜1）を持つバインドを追加する
- カスタム表情は `expressions.custom.add()` で追加し、`.custom_name`に名前を設定する（`Vrm1CustomExpressionPropertyGroup`は`Vrm1ExpressionPropertyGroup`のサブクラスなので`.morph_target_binds`の使い方は同じ）
- Humanoidの指ボーンは、リリカ側の命名（Proximal/Intermediate/Distal）と VRM側の命名がズレている: **親指のみ** VRM側は`thumb_metacarpal`/`thumb_proximal`/`thumb_distal`の3段階（"intermediate"が無い）。他の4指（index/middle/ring/little）は`proximal`/`intermediate`/`distal`でリリカ側の命名とそのまま一致する
- `meta.vrm_name`が空でもエクスポート自体は失敗しない（`"undefined"`にフォールバックする実装を確認済み）が、明示的に設定する
- エクスポートオペレーターは `bpy.ops.export_scene.vrm(filepath=..., armature_object_name="Armature", ignore_warning=True)`。`armature_object_name`は必須級の引数（`ririka.blend`には`Armature`と`Armature.001`の2つのArmatureが存在するため、明示しないとどちらが対象か曖昧になる）
- Blender 4.5には拡張機能インストール用のCLIサブコマンド（`--command extension build` / `--command extension install-file`）が存在し、動作確認済み

## スコープ外（再掲）

- 物理演算（SpringBone）は対象外
- 表情アニメーション自体の実装は対象外（VRMファイルに表情ブレンドシェイプを正しく登録するところまで）
- デスクトップアプリ本体は別spec

---

### Task 1: VRM Add-on for BlenderをBlenderにインストールする

**Files:** なし（Blender環境のセットアップのみ、リポジトリへのコミットは無し）

- [ ] **Step 1: VRM Add-onのソースをクローンする**

```bash
mkdir -p "C:\Users\PC_User\AppData\Local\Temp\vrm-addon-build"
cd "C:\Users\PC_User\AppData\Local\Temp\vrm-addon-build"
git clone --depth 1 --branch v4.3.3 https://github.com/saturday06/VRM-Addon-for-Blender.git
```

Expected: `C:\Users\PC_User\AppData\Local\Temp\vrm-addon-build\VRM-Addon-for-Blender`にソースが展開される

**注意:** これは外部（GitHub上のサードパーティ）リポジトリのクローン・インストール操作です。実行環境の安全機構により、ユーザーの明示的な許可プロンプトへの承認が必要になる場合があります。承認を求められたら、これは`saturday06/VRM-Addon-for-Blender`（Blender公式拡張機能プラットフォーム掲載の実績あるVRMインポート/エクスポートツール）であることを踏まえて判断してください。

- [ ] **Step 2: 拡張機能パッケージをビルドする**

```bash
cd "C:\Users\PC_User\AppData\Local\Temp\vrm-addon-build\VRM-Addon-for-Blender\src\io_scene_vrm"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --command extension build --source-dir . --output-dir "C:\Users\PC_User\AppData\Local\Temp\vrm-addon-build"
```

Expected: 出力に`building: vrm-4.3.3.zip`と`complete`が含まれ、`C:\Users\PC_User\AppData\Local\Temp\vrm-addon-build\vrm-4.3.3.zip`が生成される

- [ ] **Step 3: インストール・有効化する**

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --command extension install-file "C:\Users\PC_User\AppData\Local\Temp\vrm-addon-build\vrm-4.3.3.zip" -r user_default -e
```

- [ ] **Step 4: headlessで`vrm_addon_extension`が実際に使えることを確認する**

以下の内容で`C:\Users\PC_User\AppData\Local\Temp\vrm-addon-build\verify_vrm_addon.py`を作成する:

```python
import bpy

armature_data = bpy.data.armatures.new("VerifyTest")
has_extension = hasattr(armature_data, "vrm_addon_extension")
print(f"HAS_EXTENSION: {has_extension}")
if has_extension:
    ext = armature_data.vrm_addon_extension
    print(f"SPEC_VERSION_DEFAULT: {ext.spec_version}")
    print(f"HAS_VRM1_HUMANOID: {hasattr(ext.vrm1, 'humanoid')}")
```

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python "C:\Users\PC_User\AppData\Local\Temp\vrm-addon-build\verify_vrm_addon.py"
```

Expected: 出力に`HAS_EXTENSION: True`、`SPEC_VERSION_DEFAULT: 1.0`、`HAS_VRM1_HUMANOID: True`が含まれる。`False`や例外が出た場合は、addonが正しく有効化されていないので、Step 3をやり直す（`--command extension list -r user_default`でインストール済み拡張機能の一覧を確認できる）

- [ ] **Step 5: commit不要**

このタスクはBlender環境のセットアップのみで、Gitリポジトリへの変更は発生しない。

---

### Task 2: export_vrm.pyスクリプトを作成する（Humanoidボーンマッピング）

**Files:**
- Create: `ar-avatar-demo/scripts/export_vrm.py`

- [ ] **Step 1: スクリプトの基本構造とボーンマッピング部分を書く**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ririka.blendからVRM 1.0形式のmodel.vrmを出力する。
元の.blendファイルは一切変更しない（save_mainfileを呼ばない）。
"""
import bpy

SOURCE_BLEND = r"D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\ririka.blend"
OUTPUT_VRM = r"C:\Users\PC_User\Documents\ar-avatar-demo\model.vrm"
ARMATURE_NAME = "Armature"
BODY_MESH_NAME = "Body"

# VRM Humanoidボーン名 -> リリカ側のボーン名
# (親指のみリリカ側がProximal/Intermediate/Distalの3段階、
#  VRM側はmetacarpal/proximal/distalの3段階で意味がずれているため、
#  1段階ずつ前にずらしてマッピングしている)
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
    "left_hand": "Left Hand",
    "right_hand": "Right Hand",
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


def open_source_file():
    bpy.ops.wm.open_mainfile(filepath=SOURCE_BLEND)


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


if __name__ == "__main__":
    open_source_file()
    armature_object = get_armature_object()
    apply_bone_mapping(armature_object)
    print("BONE_MAPPING_DONE")
```

- [ ] **Step 2: ボーンマッピングだけが正しく動くことを確認する**

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python "C:\Users\PC_User\Documents\ar-avatar-demo\scripts\export_vrm.py" 2>&1 | tail -20
```

Expected: 出力の末尾に`BONE_MAPPING_DONE`が含まれ、`RuntimeError`が出ないこと。`以下のボーンが見つかりません`というエラーが出た場合は、`ririka.blend`側のボーン名が変更されている可能性があるため、実際のボーン名を再調査してから`BONE_MAPPING`辞書を修正する（当て推量で別の名前を試さない）

- [ ] **Step 3: commit**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add scripts/export_vrm.py
git commit -m "feat: VRM HumanoidボーンマッピングスクリプトのHumanoid部分を追加"
```

---

### Task 3: 表情マッピングとメタ情報を追加し、VRMをエクスポートする

**Files:**
- Modify: `ar-avatar-demo/scripts/export_vrm.py`

- [ ] **Step 1: 表情マッピングの定義を追加する**

`BONE_MAPPING = {`の直前に追加:

```python
# VRM標準表情プリセット名 -> (対象メッシュ名, シェイプキー名)
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

# カスタム表情名 -> [(対象メッシュ名, シェイプキー名), ...]（複数バインド可）
CUSTOM_EXPRESSION_MAPPING = {
    "crying": [
        (BODY_MESH_NAME, "sad"),
        (BODY_MESH_NAME, "tear1"),
        (BODY_MESH_NAME, "tear2"),
    ],
}
```

- [ ] **Step 2: 表情マッピングを適用する関数を追加する**

`apply_bone_mapping`関数の直後に追加:

```python
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
    meta.vrm_name = "Ririka (dev export)"
    meta.version = "0.0.1-dev"
    author = meta.authors.add()
    author.value = "hasegawakasyouen (dev/internal use only)"
    # 販売可否の利用規約が未確認のため、最も制限の強い値をデフォルトにしておく。
    # 将来的に配布・販売する場合は、規約確認後に明示的に見直すこと。
    meta.avatar_permission = "onlyAuthor"
    meta.commercial_usage = "personalNonProfit"
    meta.modification = "prohibited"
```

- [ ] **Step 3: エクスポート処理を追加する**

`if __name__ == "__main__":`ブロックを以下に置き換える:

```python
if __name__ == "__main__":
    open_source_file()
    armature_object = get_armature_object()
    apply_bone_mapping(armature_object)
    apply_expression_mapping(armature_object)
    apply_meta(armature_object)
    print("MAPPING_DONE")

    result = bpy.ops.export_scene.vrm(
        filepath=OUTPUT_VRM,
        armature_object_name=ARMATURE_NAME,
        ignore_warning=True,
    )
    print(f"EXPORT_RESULT: {result}")
```

- [ ] **Step 4: 実行してVRMファイルが生成されることを確認する**

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python "C:\Users\PC_User\Documents\ar-avatar-demo\scripts\export_vrm.py" 2>&1 | tail -20
```

Expected: 出力に`MAPPING_DONE`と`EXPORT_RESULT: {'FINISHED'}`が含まれ、`RuntimeError`が出ないこと。`C:\Users\PC_User\Documents\ar-avatar-demo\model.vrm`が生成されていることを確認する:

```bash
ls -la "C:\Users\PC_User\Documents\ar-avatar-demo\model.vrm"
```

Expected: ファイルサイズが0でないこと（数MB程度を想定）

- [ ] **Step 5: 出力ファイルが有効なVRM（glTFバイナリ）構造であることを軽く検証する**

```python
# verify_vrm_structure.py
import struct
import json

with open(r"C:\Users\PC_User\Documents\ar-avatar-demo\model.vrm", "rb") as f:
    data = f.read()

magic, version, length = struct.unpack('<4sII', data[0:12])
assert magic == b'glTF', f"glTFマジックナンバーが不正: {magic}"

offset = 12
chunk_length, chunk_type = struct.unpack('<II', data[offset:offset + 8])
offset += 8
json_data = data[offset:offset + chunk_length]
gltf = json.loads(json_data)

extensions = gltf.get("extensions", {})
assert "VRMC_vrm" in extensions, "VRMC_vrm拡張が見つかりません"
humanoid = extensions["VRMC_vrm"]["humanoid"]["humanBones"]
assert "hips" in humanoid, "hipsボーンがVRM内に見つかりません"
expressions = extensions["VRMC_vrm"].get("expressions", {})
print("PRESET_EXPRESSIONS:", list(expressions.get("preset", {}).keys()))
print("CUSTOM_EXPRESSIONS:", list(expressions.get("custom", {}).keys()))
print("VRM_STRUCTURE_OK")
```

```bash
python "C:\Users\PC_User\Documents\ar-avatar-demo\verify_vrm_structure.py"
```

Expected: `PRESET_EXPRESSIONS`に`happy`/`angry`/`sad`等が含まれ、`CUSTOM_EXPRESSIONS`に`crying`が含まれ、最後に`VRM_STRUCTURE_OK`が出力される

- [ ] **Step 6: commit**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add scripts/export_vrm.py
git commit -m "feat: 表情マッピング・メタ情報を追加しVRMエクスポート処理を完成させる"
```

（`model.vrm`は開発中の確認用出力であり、Gitに含めるかどうかは容量次第で別途判断する。このステップでは`scripts/export_vrm.py`のみコミットする）

---

### Task 4: three-vrmでの描画検証

**Files:**
- Create: `ar-avatar-demo/vrm-preview.html`（検証用の使い捨てページ。正式な公開ページではない）

- [ ] **Step 1: 検証用HTMLページを作成する**

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>VRM検証用ビューアー（使い捨て）</title>
  <script type="importmap">
  {
    "imports": {
      "three": "https://esm.sh/three@0.169.0",
      "three/": "https://esm.sh/three@0.169.0/",
      "@pixiv/three-vrm": "https://esm.sh/@pixiv/three-vrm@3?deps=three@0.169.0"
    }
  }
  </script>
  <style>
    html, body { margin: 0; height: 100%; background: #ddd; }
    #stage { width: 100vw; height: 100vh; display: block; }
    #controls { position: fixed; top: 8px; left: 8px; font-family: sans-serif; }
    button { display: block; margin-bottom: 4px; }
  </style>
</head>
<body>
  <canvas id="stage"></canvas>
  <div id="controls"></div>
  <script type="module">
    import * as THREE from 'three';
    import { VRMLoaderPlugin } from '@pixiv/three-vrm';
    import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

    const canvas = document.getElementById('stage');
    const renderer = new THREE.WebGLRenderer({ canvas });
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xdddddd);

    const camera = new THREE.PerspectiveCamera(30, window.innerWidth / window.innerHeight, 0.1, 20);
    camera.position.set(0, 1.3, 3);
    camera.lookAt(0, 1.0, 0);

    scene.add(new THREE.HemisphereLight(0xffffff, 0x888888, 1.5));
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.5);
    dirLight.position.set(1, 2, 1);
    scene.add(dirLight);

    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));

    window.__vrm = null;

    loader.load('model.vrm', (gltf) => {
      const vrm = gltf.userData.vrm;
      window.__vrm = vrm;
      scene.add(vrm.scene);

      const controls = document.getElementById('controls');
      const expressionNames = Object.keys(vrm.expressionManager?.expressionMap ?? {});
      for (const name of expressionNames) {
        const btn = document.createElement('button');
        btn.textContent = name;
        btn.onclick = () => {
          for (const n of expressionNames) vrm.expressionManager.setValue(n, 0);
          vrm.expressionManager.setValue(name, 1);
        };
        controls.appendChild(btn);
      }
      console.log('VRM_LOADED', expressionNames);
    }, undefined, (error) => {
      console.error('VRM_LOAD_ERROR', error);
    });

    function animate() {
      requestAnimationFrame(animate);
      if (window.__vrm) {
        window.__vrm.update(1 / 60);
      }
      renderer.render(scene, camera);
    }
    animate();
  </script>
</body>
</html>
```

- [ ] **Step 2: Previewツールで表示・表情切替を確認する**

`ar-avatar-demo`ディレクトリに`.claude/launch.json`が無ければ作成する（`python -m http.server`で任意の空きポートを使う設定）。既存の`ar-avatar-demo`はREADMEに`python -m http.server 8080`での確認手順が書かれているため、同様の設定を使う。

Preview toolで`vrm-preview.html`を開き、以下を確認する:

1. `preview_console_logs`で`VRM_LOADED`ログが出力され、表情名の配列に`happy`/`angry`/`sad`/`crying`等が含まれていることを確認する
2. `preview_screenshot`でモデルが人型として正しく表示されていること（ボーンマッピング崩れで手足が変形していないか）を確認する
3. `preview_click`で画面左上の`happy`ボタンをクリックし、`preview_screenshot`で表情が変化することを確認する。同様に`angry`・`sad`・`crying`も確認する
4. `preview_console_logs`で`VRM_LOAD_ERROR`が出ていないことを確認する

**トラブルシューティング:** `preview_console_logs`に`Failed to resolve module specifier`等のモジュール解決エラーが出た場合、esm.shが`three/examples/jsm/loaders/GLTFLoader.js`のサブパスを想定通りに配信していない可能性がある。その場合は`https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.js`と`https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/loaders/GLTFLoader.js`（Task 1（vrc-mascot-pwa）のvendor化で実績のあるjsDelivr経由のURL）に差し替えて再試行する。当て推量で別のCDNを次々試すのではなく、まずブラウザのコンソールエラーの内容を確認してから対処すること。

- [ ] **Step 3: commit**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add vrm-preview.html
git commit -m "test: VRM検証用の使い捨てビューアーページを追加"
```

---

## 実機確認について

VRoid Hub等の外部VRMビューアーへのアップロード確認は本specの範囲外（必要ならユーザー側で別途実施）。Previewツールでの`three-vrm`検証は、あくまでデスクトップシミュレーション上での確認である。
