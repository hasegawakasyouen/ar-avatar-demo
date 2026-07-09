# 高品質メッシュ復元 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Web公開中のアバターモデルに発生しているテクスチャ破損（黒い伸び・歪み）を解消し、元の高品質メッシュ（166,702トライアングル）に近い品質でMixamoアニメーション付きの表示を復元する。

**Architecture:** `scripts/prepare_for_mixamo.py`のデシメート処理を任意のしきい値・目標値で制御できるようにし、デシメートを最小限（可能なら無効化）に抑えたFBXをMixamoに再アップロードする。既存の`scripts/convert_to_web.py`（テクスチャ再リンク・PBR調整・アニメーション合成）は変更しない。

**Tech Stack:** Blender 4.5（bpy headless script）、Mixamo（web、手動操作）

**確認済みの環境:**
- 元の高品質FBX: `D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\FBX\ririka.fbx`（166,702トライアングル・14メッシュ・337ボーン）
- 現在の`ar-avatar-demo\source\*.fbx`（Mixamo出力）はgitで追跡されている（`.gitignore`に`*.fbx`のエントリなし）
- `scripts/prepare_for_mixamo.py`は`DECIMATE_THRESHOLD = 30000`・`DECIMATE_TARGET = 25000`をモジュールレベル定数として持つ

---

### Task 1: `prepare_for_mixamo.py`にデシメート制御用CLI引数を追加する

**Files:**
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\scripts\prepare_for_mixamo.py`

- [ ] **Step 1: `get_args()`の直後に`parse_args()`を追加し、`main()`を書き換える**

`scripts/prepare_for_mixamo.py`の`get_args()`関数の直後に、以下の関数を追加する:

```python
def parse_args(args):
    positional = []
    decimate_threshold = DECIMATE_THRESHOLD
    decimate_target = DECIMATE_TARGET
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--decimate-threshold":
            decimate_threshold = int(args[i + 1])
            i += 2
        elif arg == "--decimate-target":
            decimate_target = int(args[i + 1])
            i += 2
        else:
            positional.append(arg)
            i += 1
    if len(positional) != 2:
        raise SystemExit("Expected 2 positional args: <input_fbx> <output_fbx>")
    input_fbx, output_fbx = positional
    return input_fbx, output_fbx, decimate_threshold, decimate_target
```

`decimate_if_needed()`関数を、モジュールレベル定数を直接参照する代わりに引数を受け取るように書き換える:

```python
def decimate_if_needed(mesh_obj, threshold, target):
    tris = count_triangles(mesh_obj)
    if tris <= threshold:
        print(f"PREPARE_INFO triangles={tris} <= threshold={threshold}, skipping decimate")
        return
    ratio = target / tris
    mod = mesh_obj.modifiers.new(name="Decimate", type='DECIMATE')
    mod.ratio = ratio
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    print(f"PREPARE_INFO decimated from {tris} to ~{count_triangles(mesh_obj)} triangles")
```

`main()`関数を以下のように書き換える:

```python
def main():
    args = get_args()
    input_fbx, output_fbx, decimate_threshold, decimate_target = parse_args(args)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=input_fbx)

    mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']

    remove_shape_keys(mesh_objs)
    joined = join_meshes(mesh_objs)
    decimate_if_needed(joined, decimate_threshold, decimate_target)
    strip_armature([joined])

    bpy.ops.export_scene.fbx(filepath=output_fbx, use_selection=False, add_leaf_bones=False)
    print("PREPARE_OK", output_fbx)
```

`get_args()`のUsage文字列も更新する:

```python
def get_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python prepare_for_mixamo.py "
            "-- <input_fbx> <output_fbx> [--decimate-threshold N] [--decimate-target N]"
        )
    return argv[argv.index("--") + 1:]
```

- [ ] **Step 2: デフォルト引数（後方互換性）を確認する**

引数を省略した場合、以前と同じ挙動（166,702トライアングルの元FBXは30,000を超えるため25,000程度にデシメートされる）になることを確認する:

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\prepare_for_mixamo.py -- "D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\FBX\ririka.fbx" "%TEMP%\claude\prepare_default_test.fbx"
```

Expected（出力に以下が含まれる）: `PREPARE_INFO decimated from 166702 to ~2` で始まる行（25,000前後）、`PREPARE_OK`

- [ ] **Step 3: `--decimate-threshold`オプションでデシメート無効化を確認する**

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\prepare_for_mixamo.py -- "D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\FBX\ririka.fbx" "%TEMP%\claude\prepare_nodeci_test.fbx" --decimate-threshold 200000
```

Expected（出力に以下が含まれる）: `PREPARE_INFO triangles=166702 <= threshold=200000, skipping decimate`、`PREPARE_OK`

- [ ] **Step 4: 生成されたFBXのポリゴン数・メッシュ数・シェイプキー数を検証する**

以下のPythonスクリプトを一時ファイル（例: `%TEMP%\claude\verify_prepare.py`）として作成する:

```python
import bpy, sys
argv = sys.argv[sys.argv.index("--") + 1:]
fbx_path = argv[0]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx_path)
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
armature_objs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
total_tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in mesh_objs)
has_shape_keys = any(o.data.shape_keys for o in mesh_objs)
print(f"VERIFY mesh_count={len(mesh_objs)} total_tris={total_tris} armature_count={len(armature_objs)} has_shape_keys={has_shape_keys}")
```

これを`%TEMP%\claude\prepare_nodeci_test.fbx`に対して実行する:

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python "%TEMP%\claude\verify_prepare.py" -- "%TEMP%\claude\prepare_nodeci_test.fbx"
```

Expected: `VERIFY mesh_count=1 total_tris=166702 armature_count=0 has_shape_keys=False`

- [ ] **Step 5: 一時ファイルを削除する**

```bash
rm -f "%TEMP%\claude\prepare_default_test.fbx" "%TEMP%\claude\prepare_nodeci_test.fbx" "%TEMP%\claude\verify_prepare.py"
```

- [ ] **Step 6: コミット**

```bash
git add scripts/prepare_for_mixamo.py
git commit -m "feat: add configurable decimate threshold/target CLI args to prepare_for_mixamo.py"
```

---

### Task 2: デシメート無効化でフル品質版FBXを生成する

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_full_for_mixamo.fbx`
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\.gitignore`

- [ ] **Step 1: `.gitignore`に一時アップロード用ファイルを追加する**

`C:\Users\PC_User\Documents\ar-avatar-demo\.gitignore`に以下の1行を追加する:

```
source/avatar_full_for_mixamo.fbx
```

（このファイルはMixamoへの一時アップロード用であり、Task 3完了後は`source/avatar_*_mixamo.fbx`3ファイルに置き換わるため、リポジトリには含めない）

- [ ] **Step 2: フル品質版FBXを生成する**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\prepare_for_mixamo.py -- "D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\FBX\ririka.fbx" source\avatar_full_for_mixamo.fbx --decimate-threshold 200000
```

Expected: `PREPARE_INFO triangles=166702 <= threshold=200000, skipping decimate`、`PREPARE_OK source\avatar_full_for_mixamo.fbx`

- [ ] **Step 3: コミット**

```bash
git add .gitignore
git commit -m "chore: gitignore temporary full-quality FBX for Mixamo upload"
```

（`source\avatar_full_for_mixamo.fbx`自体はgitignore対象のためステージされない）

---

### Task 3: Mixamoへアップロードしてアニメーションを再取得する（手動ステップ）

**Files:**
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_idle_mixamo.fbx`
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_wave_mixamo.fbx`
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_dance_mixamo.fbx`

このタスクはユーザーの手動操作が必要なため、サブエージェントには委譲せず、ユーザーに直接依頼する。

- [ ] **Step 1: Mixamo（https://www.mixamo.com/）に`source\avatar_full_for_mixamo.fbx`をアップロードし、オートリギングを実行する**

以前と同じ手順（[Prepare] Task 1〜2で確立済み）。ポリゴン数が166,702と多いため、以前ハングした前例がある点に注意。数分待っても完了しない場合は失敗とみなし、Task 5（フォールバック）に進む。

- [ ] **Step 2: オートリギング成功後、idle・wave・danceの3アニメーションをそれぞれFBXでダウンロードする**

以前と同じ設定（フォーマット: FBX Binary、以前のダウンロードと同条件）でダウンロードする。

- [ ] **Step 3: ダウンロードした3ファイルで`source\`内の既存ファイルを置き換える**

```
avatar_idle_mixamo.fbx
avatar_wave_mixamo.fbx
avatar_dance_mixamo.fbx
```

- [ ] **Step 4: 置き換え完了をこの会話で報告する**

成功した場合はTask 4に進む。Mixamoが失敗・ハングした場合はその旨を報告し、Task 5（フォールバック）に進む。

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

- [ ] **Step 2: ファイルサイズを確認する**

```bash
ls -la model.glb model.usdz
```

現状（修正前）はmodel.glb=7,264,540バイト・model.usdz=9,030,383バイト。今回はメッシュのポリゴン数が大幅に増えるため、サイズ増加が見込まれる。目安として30MBを超える場合はモバイルパフォーマンス上の懸念があるため、この会話で報告し対応を相談する。

- [ ] **Step 3: ブラウザプレビューでスクリーンショットを撮り、黒破損が解消されていることを確認する**

ローカルサーバーで`model.glb`を表示し、スクリーンショットを撮る。顔・胴体・脚のテクスチャの伸び・黒い破損が解消され、以前のスクリーンショット（2026-07-09に撮影、黒い破損あり）と比較して明らかに改善していることを確認する。

- [ ] **Step 4: 3アニメーション・33ジョイントスキンなど既存機能への回帰がないことを確認する**

GLBのJSONチャンクを解析し、以下を確認する:
- `animations`配列に3エントリ（idle/wave/dance）あること
- `skins`配列に1エントリあり、Mixamoの33ジョイントであること
- `metal`/`Diamond`/`pearl`/`chain`/`tear`の各マテリアル値が[Accent]作業で設定した値のまま維持されていること

- [ ] **Step 5: コミット**

```bash
git add model.glb model.usdz
git commit -m "asset: regenerate model.glb/usdz from full-quality (non-decimated) mesh"
```

- [ ] **Step 6: 一時ファイルを削除する**

```bash
rm -f source/avatar_full_for_mixamo.fbx
```

---

### Task 5: フォールバック — 軽めのデシメートで再試行する（Task 3でMixamoが失敗した場合のみ実行）

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_full_for_mixamo.fbx`（Task 2の出力を上書き）

このタスクはTask 3でMixamoのオートリギングがハング・失敗した場合にのみ実行する。成功していればスキップする。

- [ ] **Step 1: 軽めのターゲットでFBXを再生成する**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\prepare_for_mixamo.py -- "D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\FBX\ririka.fbx" source\avatar_full_for_mixamo.fbx --decimate-threshold 30000 --decimate-target 90000
```

Expected: `PREPARE_INFO decimated from 166702 to ~90000 triangles`、`PREPARE_OK`

- [ ] **Step 2: Task 3のStep 1〜4を再実行する**

再生成した`source\avatar_full_for_mixamo.fbx`をMixamoにアップロードし、オートリギング→3アニメーション取得→`source\`内ファイル置き換えを行う。これでも失敗する場合はこの会話で報告し、ターゲット値をさらに下げて（例: 50,000）再試行するか、品質優先・静止ポーズ表示への切り替えを検討する。

- [ ] **Step 3: 成功したらTask 4に進む**

---

### Task 6: 両プロジェクトへデプロイする

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

`sw.js`冒頭の`CACHE_VERSION`を確認し、次の番号に上げる（現在`'mascot-cache-v4'`のはずなので`'mascot-cache-v5'`にする。実際の現在値を確認してから次の番号にすること）。

- [ ] **Step 4: コミット・push**

```bash
cd "C:\Users\PC_User\Documents\vrc-mascot-pwa"
git add model.glb model.usdz sw.js
git commit -m "asset: apply full-quality mesh, bump cache version"
git push
```

- [ ] **Step 5: 公開サイトの反映を確認する**

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://hasegawakasyouen.github.io/vrc-mascot-pwa/model.glb
```

---

### Task 7: iPhone実機で確認する（手動）

**Files:** なし

- [ ] **Step 1: `ar-avatar-demo`の公開URLをiPhoneのSafariで開く**

`https://hasegawakasyouen.github.io/ar-avatar-demo/` を開き、黒い破損が解消されていること、読み込み速度・操作の滑らかさに問題がないか確認する。

- [ ] **Step 2: `vrc-mascot-pwa`をiPhoneで開く**

同様の見た目確認に加え、タップでのアニメーション切り替え・AR起動が引き続き問題ないことを確認する。

- [ ] **Step 3: 問題があれば記録**

ファイルサイズやパフォーマンスに問題があれば、この会話で報告し軽量化方針（デシメートターゲットの調整）を相談する。

---

## Self-Review メモ

- **Spec網羅性**: design specの各要素（原因特定/CLI引数化/フル品質版生成/Mixamo再取得/再変換検証/フォールバック/両プロジェクトデプロイ/実機確認）に対応するTaskをすべて用意した
- **プレースホルダ**: 「TBD」「後で」は含まない。Task 5は実行条件（Task 3失敗時のみ）を明記した具体的な条件分岐であり、曖昧な保留ではない
- **型/名称の一貫性**: `decimate_if_needed(mesh_obj, threshold, target)`のシグネチャ変更はTask 1内で完結しており、他タスクからの呼び出しはない
- **既存機能への影響**: `convert_to_web.py`・`tune_material_pbr_values()`・テクスチャ再リンクには一切触れないため、Task 4のStep 4で回帰確認を明記した
