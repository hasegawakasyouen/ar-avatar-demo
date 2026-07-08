# Blenderパイプライン半自動化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 骨格ストリップ・デシメートを自動化する新規スクリプト `scripts/prepare_for_mixamo.py` を追加し、生のVRChatアバターFBXからMixamoアップロード用メッシュのみFBXを1コマンドで生成できるようにする。

**Architecture:** 既存の `scripts/convert_to_web.py` とは独立した新規スクリプトを追加する。入力FBXをインポート→Shape Key削除→メッシュ統合→（閾値超過時のみ）デシメート→骨格削除→FBX書き出し、という一連の流れを1回のBlenderセッションで行う。

**Tech Stack:** Blender 4.5（bpy headless script）

**確認済みの環境:**
- Blender: `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`
- 高ポリゴンテストデータ: `D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\FBX\ririka.fbx`（166,702トライアングル、VRChat用骨格つき。読み取り専用として扱い、変更しない）
- 低ポリゴン（閾値以下）テストデータ: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_idle_mixamo.fbx`（33ボーン骨格つき、約25,000トライアングル。既にこのプロジェクトにコミット済みのファイルを読み取り専用で使う）

---

### Task 1: `scripts/prepare_for_mixamo.py` を作成する

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\scripts\prepare_for_mixamo.py`

- [ ] **Step 1: スクリプトを書く**

```python
# scripts/prepare_for_mixamo.py
import bpy
import sys

DECIMATE_THRESHOLD = 30000  # このトライアングル数を超えたらデシメート
DECIMATE_TARGET = 25000     # デシメート後の目標トライアングル数


def get_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python prepare_for_mixamo.py "
            "-- <input_fbx> <output_fbx>"
        )
    return argv[argv.index("--") + 1:]


def count_triangles(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def remove_shape_keys(mesh_objs):
    for obj in mesh_objs:
        if obj.data.shape_keys:
            while obj.data.shape_keys:
                obj.shape_key_remove(obj.data.shape_keys.key_blocks[0])


def join_meshes(mesh_objs):
    if len(mesh_objs) == 1:
        return mesh_objs[0]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def decimate_if_needed(mesh_obj):
    tris = count_triangles(mesh_obj)
    if tris <= DECIMATE_THRESHOLD:
        print(f"PREPARE_INFO triangles={tris} <= threshold={DECIMATE_THRESHOLD}, skipping decimate")
        return
    ratio = DECIMATE_TARGET / tris
    mod = mesh_obj.modifiers.new(name="Decimate", type='DECIMATE')
    mod.ratio = ratio
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    print(f"PREPARE_INFO decimated from {tris} to ~{count_triangles(mesh_obj)} triangles")


def strip_armature(mesh_objs):
    for obj in mesh_objs:
        for mod in list(obj.modifiers):
            if mod.type == 'ARMATURE':
                obj.modifiers.remove(mod)
        if obj.parent and obj.parent.type == 'ARMATURE':
            matrix_world = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = matrix_world

    for obj in list(bpy.data.objects):
        if obj.type == 'ARMATURE':
            bpy.data.objects.remove(obj, do_unlink=True)


def main():
    args = get_args()
    if len(args) != 2:
        raise SystemExit("Expected 2 args: <input_fbx> <output_fbx>")
    input_fbx, output_fbx = args

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=input_fbx)

    mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']

    remove_shape_keys(mesh_objs)
    joined = join_meshes(mesh_objs)
    decimate_if_needed(joined)
    strip_armature([joined])

    bpy.ops.export_scene.fbx(filepath=output_fbx, use_selection=False, add_leaf_bones=False)
    print("PREPARE_OK", output_fbx)


main()
```

**設計メモ（実装者向け）:**
- Shape Key削除は必ずJoinより前に行う（オブジェクトごとにShape Keyの有無・内容が異なると`bpy.ops.object.join()`の挙動が不安定になるため）
- Decimateは必ずShape Key削除より後・骨格削除より前に行う（Decimate ModifierはShape Keyがあると適用できないため）
- `strip_armature`は既存の類似処理（過去のトラブルシューティングで使ったパターン）と同じ考え方: Armature ModifierとArmatureオブジェクトを削除し、パースの際にワールド変換を保持する

- [ ] **Step 2: コミット**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add scripts/prepare_for_mixamo.py
git commit -m "feat: add prepare_for_mixamo.py to automate skeleton-strip and decimation"
```

---

### Task 2: 高ポリゴン・VRChat骨格ケースで実行・検証する

**Files:** なし（一時的な出力ファイルのみ、コミット不要）

- [ ] **Step 1: 実際の高ポリゴンデータで実行する**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\prepare_for_mixamo.py -- "D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\FBX\ririka.fbx" prepare_test_high.fbx
```

Expected: `PREPARE_INFO decimated from 166702 to ~25000程度 triangles` のようなログと、`PREPARE_OK prepare_test_high.fbx` が出力される。終了コード0。

- [ ] **Step 2: 出力FBXを検証する**

Blenderで出力FBXを再インポートし、以下を確認する:
- Armatureオブジェクトが0件であること（骨格が正しく削除されている）
- メッシュが1つに統合されていること
- トライアングル数が約25,000（DECIMATE_TARGET付近）であること

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\prepare_for_mixamo.py -- --check-only prepare_test_high.fbx
```

（↑のような別チェック用コマンドは作らず、単純なPythonワンライナーでBlenderに読み込ませて`bpy.data.objects`の内訳を出力する形で確認してよい。実装者の裁量で確認方法を選んでよいが、実際に確認すること。）

- [ ] **Step 3: 一時ファイルを削除**

```bash
rm prepare_test_high.fbx
```

---

### Task 3: 低ポリゴン（閾値以下）ケースで検証する

**Files:** なし

- [ ] **Step 1: 閾値以下のデータで実行する**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\prepare_for_mixamo.py -- source\avatar_idle_mixamo.fbx prepare_test_low.fbx
```

Expected: `PREPARE_INFO triangles=25004程度 <= threshold=30000, skipping decimate` のようなログが出て、デシメートがスキップされることを確認する。`PREPARE_OK prepare_test_low.fbx` が出力される。

- [ ] **Step 2: 出力FBXを検証する**

骨格が正しく削除されていること、トライアングル数がほぼ変化していない（デシメートされていない）ことを確認する。

- [ ] **Step 3: 一時ファイルを削除**

```bash
rm prepare_test_low.fbx
```

---

### Task 4: READMEを更新する

**Files:**
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\README.md`

- [ ] **Step 1: 現在のREADMEを読み、Step 2（骨格ストリップ）とStep 3内のデシメート説明の位置を確認する**

- [ ] **Step 2: Step 2・Step 3のデシメート部分の冒頭に、自動化スクリプトの案内を追記する**

既存の手動手順（Blender GUIでの骨格削除・デシメート）は残しつつ、その前に以下を追記する（既存の文章構成に合わせて自然な位置に挿入すること）:

```markdown
> **自動化スクリプトを使う場合（推奨）:**
> 以下のコマンドで、骨格ストリップとデシメート（頂点数が3万トライアングルを超える場合のみ、約25,000まで自動削減）を1回で行えます。GUIでの手作業（下記）は、このスクリプトを使わない場合のみ必要です。
>
> ```bash
> "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\prepare_for_mixamo.py -- <生のVRChatアバターFBX> avatar_meshonly.fbx
> ```
>
> 出力された `avatar_meshonly.fbx` をそのままMixamoにアップロードできます。
```

- [ ] **Step 3: コミット・push**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add README.md
git commit -m "docs: document prepare_for_mixamo.py automation script"
git push
```

---

## Self-Review メモ

- **Spec網羅性**: design specの各要素（Shape Key削除/メッシュ統合/条件付きデシメート/骨格ストリップ/動作確認）に対応するTaskをすべて用意した
- **プレースホルダ**: 「TBD」「後で」は含まない
- **型/名称の一貫性**: `DECIMATE_THRESHOLD`/`DECIMATE_TARGET`の値（30000/25000）はスクリプト本体・Task 2/3の期待値・READMEの説明文で一貫している
- **既存スクリプトへの影響**: `scripts/convert_to_web.py`は一切変更しないため、そちらのスモークテスト再実行は不要（design specの通り）
