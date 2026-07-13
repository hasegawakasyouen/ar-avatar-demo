# ririka_kaihen.vrm 衣装混在・表情破綻の修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ririka_kaihen.vrmを、ユーザー提供のリファレンス画像（黒猫悪夢衣装: 猫耳＋肉球グローブ＋黒レースドレス＋黒レースソックス、羽なし、口を閉じたニュートラル表情）どおりの見た目に修正し、desktop-vrm-mascotが使う5表情（happy/relaxed/surprised/sad/crying）を正常動作させる。

**Architecture:** 既存パイプライン（`ririka 黒猫悪夢(Clone).fbx` → `prepare_ririka_kaihen_blend.py` → `source/ririka_kaihen.blend` → `export_vrm_ririka_kaihen.py` → `ririka_kaihen.vrm`）の`prepare`段に、(1)調査で特定した混入メッシュの非表示化リスト追加、(2)Basis以外のシェイプキーのデフォルト値リセット（体型カスタマイズ用の例外allowlist付き）の2修正を加え、パイプライン全体を再実行する。blendファイルの手動編集はしない。

**Tech Stack:** Blender 4.5（prepare段・FBXインポート）+ Blender 5.1（export段・VRM Add-on）+ three-vrm（`vrm-preview.html`によるブラウザ実機検証）

**設計書:** `docs/superpowers/specs/2026-07-13-ririka-kaihen-costume-expression-fix-design.md`

---

## 前提知識（実装前に必ず把握しておくこと）

- **リファレンスの見た目（ユーザー提供画像の言語化）**: ピンク髪（黒メッシュ入り）のキャラクター。黒い猫耳（内側に白いファー）、両手に黒い肉球グローブ（掌側にピンクの肉球）、黒いシースルー/レースのドレス（白いファートリムと白黒のポンポン飾り付き）、膝下に黒いレースソックス、黒い猫しっぽ。**太ももは素肌**（黒レース調ではない — 前回「未解決」とされた太ももの件は、この新リファレンスでは素肌が正しい）。**腰・背中に羽は存在しない**（ユーザー確認済み）。表情は口を閉じた落ち着いたニュートラル。
- **現状の壊れ方**: (1) 上記に加えて別衣装系のメッシュと腰の羽状パーツが混ざって表示されている。(2) 口が開きっぱなしで、目にも意図しない模様が乗っている。
- **口・目の破綻の最有力仮説**: FBXにはUnity側SkinnedMeshRendererのblendshapeウェイトがシェイプキーの`value`としてそのまま入ってくる。ベイク時点で表情系シェイプキー（`vrc.v_aa`等のビゼムや目関連）が非0のまま残っていた場合、VRMエクスポート時にglTFのmorph target初期ウェイトとして焼き込まれ、常時口が開く。ただし**体型カスタマイズ系のシェイプキー（胸・体格調整等）が意図的に非0にされている可能性もあり、それは保持すべき**。だからこそ全リセットではなく「調査→例外allowlist付きリセット」の構造にする。
- **メッシュ非表示化の仕組み（既存）**: `prepare_ririka_kaihen_blend.py`に`PROP_MESH_NAMES_TO_HIDE`（小道具46個）と`DEFAULT_OUTFIT_MESH_NAMES_TO_HIDE`（別デフォルト私服5個: Outer/Boots/Cloth/cover_arm/Over_knee_socks）の2リストが既にあり、`hide_viewport=True`にするとVRM Add-onのエクスポート対象から除外される。**この2リストで既に隠しているのに混入が残っている＝リストから漏れているメッシュがある**、が今回の前提。
- **Blenderバージョンの使い分け（前回踏襲）**: prepare段（FBXインポート）はBlender 4.5、export段（VRM Add-on）はBlender 5.1。混ぜないこと。
- **検証時のキャッシュバスティング必須**: ブラウザ確認は毎回`vrm-preview.html?t=<現在時刻>`のようにクエリを変えて開く。前回、古いキャッシュを見て誤判定した実績がある。
- **アーティファクトは全てgit未追跡**: `ririka_kaihen.vrm`・`source/ririka_kaihen.blend`・`model.vrm`はコミットしない（現状も未追跡）。コミット対象はスクリプトの変更のみ。
- **完成判定はユーザーの目視承認**（設計書の要件）。エージェントの判断だけで完了としない。

---

### Task 1: 調査（メッシュ棚卸し＋シェイプキー監査）

**Files:**
- Create: `ar-avatar-demo/scripts/_audit_ririka_kaihen.py`（一時調査スクリプト、コミットしない）

- [ ] **Step 1: 調査スクリプトを作成する**

```python
# scripts/_audit_ririka_kaihen.py
# 一時調査スクリプト（コミットしない）:
# source/ririka_kaihen.blend の全メッシュ棚卸しと非0シェイプキーの監査を行う。
import bpy
import mathutils

BLEND_PATH = r"C:\Users\PC_User\Documents\ar-avatar-demo\source\ririka_kaihen.blend"

bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)

print("=== MESH_INVENTORY (name | hide_viewport | polys | bbox_center | bbox_dims | materials) ===")
for obj in sorted(bpy.data.objects, key=lambda o: o.name):
    if obj.type != 'MESH':
        continue
    corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
    center = ((min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2)
    dims = (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
    mats = [m.name for m in obj.data.materials if m is not None]
    print(f"{obj.name} | hidden={obj.hide_viewport} | polys={len(obj.data.polygons)} | "
          f"center=({center[0]:.2f},{center[1]:.2f},{center[2]:.2f}) | "
          f"dims=({dims[0]:.2f},{dims[1]:.2f},{dims[2]:.2f}) | mats={mats}")

print("=== NONZERO_SHAPE_KEYS (mesh :: key = value) ===")
found = 0
for obj in sorted(bpy.data.objects, key=lambda o: o.name):
    if obj.type != 'MESH' or obj.data.shape_keys is None:
        continue
    for kb in obj.data.shape_keys.key_blocks:
        if kb.name == 'Basis':
            continue
        if abs(kb.value) > 1e-6:
            print(f"{obj.name} :: {kb.name} = {kb.value:.4f} (mute={kb.mute})")
            found += 1
print(f"NONZERO_SHAPE_KEY_COUNT: {found}")
```

- [ ] **Step 2: 調査スクリプトを実行し、出力を保存する**

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python "C:\Users\PC_User\Documents\ar-avatar-demo\scripts\_audit_ririka_kaihen.py" > "C:\Users\PC_User\Documents\ar-avatar-demo\_audit_output.txt" 2>&1
```

Expected: `MESH_INVENTORY`セクションに全メッシュ（前回監査時点で77個）、`NONZERO_SHAPE_KEYS`セクションに非0シェイプキーの一覧が出力される。`NONZERO_SHAPE_KEY_COUNT`が0の場合、口の破綻の原因は別（表情マッピング側）にあるため、`export_vrm_ririka_kaihen.py`の`PRESET_EXPRESSION_MAPPING`と、VRMエクスポート後のglTF JSONのmorph target初期ウェイトを追加調査する（エスカレーション: 判断に迷う場合はDONE_WITH_CONCERNSで報告し、オーケストレーターの判断を仰ぐ）。

- [ ] **Step 3: 出力を分析し、「隠すべき混入メッシュ」候補を特定する**

分析観点:
1. `hidden=False`（＝現在エクスポートされている）メッシュのうち、リファレンスの見た目（前提知識セクション参照）に**含まれないもの**を列挙する。特に「羽」: 腰の高さ（center z≈0.7前後）で左右に広がる（dims xが大きい）メッシュが最有力。名前に`wing`/`Wing`/`hane`等が含まれる可能性も高い
2. 判断に迷うメッシュは、単体ハイライトレンダリングで視覚確認する（下記Step 4）
3. 非0シェイプキーを2分類する: **(a) 表情・ビゼム系**（`vrc.v_*`、`mouth_*`、`eye*`、`blink*`、`brow_*`、`happy`/`sad`等の顔関連 → リセット対象）、**(b) 体型カスタマイズ系**（胸・体格・身長系の名前 → 保持候補としてオーケストレーターに報告）

- [ ] **Step 4: （必要な場合のみ）疑わしいメッシュを単体レンダリングで視覚確認する**

名前と座標だけで判断できないメッシュがある場合、以下の一時スクリプトで対象メッシュのみを表示したレンダリングを行う:

```python
# scripts/_render_single_mesh.py （一時スクリプト、コミットしない）
# 使い方: blender --background --python _render_single_mesh.py -- <メッシュ名> <出力PNG>
import sys
import bpy

BLEND_PATH = r"C:\Users\PC_User\Documents\ar-avatar-demo\source\ririka_kaihen.blend"
args = sys.argv[sys.argv.index("--") + 1:]
target_name, output_png = args[0], args[1]

bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.hide_render = (obj.name != target_name)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') else 'BLENDER_EEVEE'
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.filepath = output_png

# 正面からのカメラを配置（キャラクターは原点付近、身長約1.4m）
cam_data = bpy.data.cameras.new("AuditCam")
cam_obj = bpy.data.objects.new("AuditCam", cam_data)
scene.collection.objects.link(cam_obj)
cam_obj.location = (0.0, -2.5, 0.8)
cam_obj.rotation_euler = (1.5708, 0.0, 0.0)
scene.camera = cam_obj

light_data = bpy.data.lights.new("AuditLight", type='SUN')
light_obj = bpy.data.objects.new("AuditLight", light_data)
scene.collection.objects.link(light_obj)
light_obj.rotation_euler = (0.8, 0.0, 0.0)

bpy.ops.render.render(write_still=True)
print(f"RENDERED: {output_png}")
```

- [ ] **Step 5: 調査結果を報告する（コミットなし）**

以下をまとめて報告する:
- 隠すべき混入メッシュの確定リスト（メッシュ名と判断根拠）
- リセット対象のシェイプキー一覧（表情・ビゼム系）
- 保持候補のシェイプキー一覧（体型カスタマイズ系、あれば）と判断理由
- 一時スクリプト（`_audit_ririka_kaihen.py`・`_render_single_mesh.py`）と`_audit_output.txt`は削除せず残す（Task 2で参照後、Task 2の担当が削除する）

**エスカレーション条件（設計書より）**: 調査で「あるべき黒猫悪夢衣装のメッシュがFBXに存在しない」または「複数衣装が1メッシュに結合されており分離不能」と判明した場合はBLOCKEDで報告し、Unity再ベイク（方針B）への切替判断をオーケストレーターに委ねる。

---

### Task 2: prepareスクリプト拡張（混入メッシュ非表示＋シェイプキーリセット）

**Files:**
- Modify: `ar-avatar-demo/scripts/prepare_ririka_kaihen_blend.py`
- Delete: `ar-avatar-demo/scripts/_audit_ririka_kaihen.py`・`ar-avatar-demo/scripts/_render_single_mesh.py`・`ar-avatar-demo/_audit_output.txt`（一時ファイルの後片付け）

前提: Task 1の報告（隠すメッシュ確定リスト・リセット対象シェイプキー・保持候補）を受け取っていること。保持候補がある場合はオーケストレーター経由でユーザーの判断を仰いでから着手する。

- [ ] **Step 1: 混入メッシュの非表示化リストを追加する**

`prepare_ririka_kaihen_blend.py`の`DEFAULT_OUTFIT_MESH_NAMES_TO_HIDE`定義の直後に、Task 1で確定したメッシュ名リストを追加する:

```python
# ユーザーの実見確認（desktop-vrm-mascotでの使用時）で発覚した衣装混在の修正:
# リファレンス画像（黒猫悪夢衣装: 猫耳＋肉球グローブ＋黒レースドレス＋黒レース
# ソックス、羽なし）と照合し、Task 1の調査（メッシュ棚卸し＋単体レンダリング
# 確認）で「リファレンスに存在しない混入パーツ」と判定したメッシュ。
# 腰の羽状パーツはユーザー確認済みで「本来存在しないパーツ」。
MIXED_IN_MESH_NAMES_TO_HIDE = [
    "Bag",  # 「腰の羽」の正体: コウモリ羽付きリュック（単体レンダリングで形状確認済み）。
            # 材質が隠蔽済みデフォルト私服と同族（cloth1/metal/Diamond/pearl）
    "cloth_Accessories",  # 隠蔽済み私服「Cloth」の付属アクセサリー一式
                          # （頭部のミニコウモリ羽クリップ・耳飾り・腰ストリップ）
    "pet",  # スケール0で全次元dims=0の死にジオメトリ（3146ポリゴンが1点に潰れた状態）。
            # 現状は見えないが、無駄ポリゴン排除と将来の出現防止のため非表示にする
]
```

- [ ] **Step 2: 非表示化処理の重複を共通ヘルパーに集約し、新リストを配線する**

既存の`hide_prop_meshes()`と`hide_default_outfit_meshes()`は同一ロジックの重複のため、共通ヘルパーに集約する。**既存の`hide_prop_meshes()`と`hide_default_outfit_meshes()`の2関数定義（重複した実装本体）をまるごと削除し**、同じ場所に以下（共通ヘルパー`_hide_meshes()`＋3つの薄いラッパー）を配置する:

```python
def _hide_meshes(names, label):
    """指定名のメッシュのhide_render・hide_viewportを両方Trueにする。

    VRM Add-onのエクスポート対象オブジェクト選定ロジック
    （editor/search.py の export_objects()）は、export_invisiblesが
    Falseの場合（本パイプラインのデフォルト、export_vrm_ririka_kaihen.pyでも
    未指定のためFalseのまま）、Object.visible_get()がFalseのオブジェクトを
    除外する。visible_get()はhide_viewportの状態（および所属コレクションの
    hide_viewport）に依存するため、実際にエクスポートから除外するために
    必須なのはhide_viewport=Trueである。hide_renderはこのフィルタには
    使われないが、「レンダリング/エクスポートに含めない」という意図を
    Blender上のUIでも一貫して示すため、あわせてTrueにしておく。
    """
    missing = []
    hidden = []
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != 'MESH':
            missing.append(name)
            continue
        obj.hide_render = True
        obj.hide_viewport = True
        hidden.append(name)

    if missing:
        raise RuntimeError(f"以下の{label}メッシュが見つかりません: {missing}")

    return hidden


def hide_prop_meshes():
    """PROP_MESH_NAMES_TO_HIDEに列挙した「本体と無関係な小道具/UIメッシュ」を非表示化する。"""
    return _hide_meshes(PROP_MESH_NAMES_TO_HIDE, "小道具/UI")


def hide_default_outfit_meshes():
    """DEFAULT_OUTFIT_MESH_NAMES_TO_HIDEに列挙した「本物の別デフォルト私服」を非表示化する。"""
    return _hide_meshes(DEFAULT_OUTFIT_MESH_NAMES_TO_HIDE, "デフォルト私服")


def hide_mixed_in_meshes():
    """MIXED_IN_MESH_NAMES_TO_HIDEに列挙した「リファレンスに存在しない混入パーツ」を非表示化する。"""
    return _hide_meshes(MIXED_IN_MESH_NAMES_TO_HIDE, "混入パーツ")
```

- [ ] **Step 3: 【調査結果による改訂】表情バインドの二重登録を修正する（export_vrm_ririka_kaihen.py）**

> **改訂の経緯（Task 1調査結果）**: 当初仮説の「シェイプキー焼き込み」は棄却された（blend内の非0シェイプキーは0個、glTF初期ウェイトも全0）。真因は表情バインドの二重登録 — VRM Add-onがVRChat由来のシェイプキー名（`vrc.v_*`・「まばたき」等）から自動でバインドを割り当て済みのところへ、`apply_expression_mapping()`が既存バインドをクリアせず追加していた。そのためシェイプキーリセット処理は追加せず（YAGNI）、代わりにこの修正を行う。

`scripts/export_vrm_ririka_kaihen.py`の`apply_expression_mapping()`を以下に置き換える:

```python
def apply_expression_mapping(armature_object):
    expressions = armature_object.data.vrm_addon_extension.vrm1.expressions

    for preset_name, binds in PRESET_EXPRESSION_MAPPING.items():
        expression = getattr(expressions.preset, preset_name)
        # VRM Add-onはVRChat由来のシェイプキー名（vrc.v_*・「まばたき」・「笑い」等）
        # から一部プリセットへ自動でmorph_target_bindsを割り当てる。この上へ
        # 本スクリプトのマッピングを無条件に追加すると同一シェイプキーが
        # 二重バインドされ、ランタイムで実効2倍のウェイトがかかる
        # （実害: リップシンクの口が2倍振幅で開きっぱなしに見える・
        # まぶたの二重変形が「目の模様」に見える）。本スクリプトの
        # マッピングを唯一の正とするため、追加前に既存バインドをクリアする。
        expression.morph_target_binds.clear()
        for mesh_name, shape_key_name in binds:
            _add_morph_target_bind(expression, mesh_name, shape_key_name)

    for custom_name, binds in CUSTOM_EXPRESSION_MAPPING.items():
        custom_expression = expressions.custom.add()
        custom_expression.custom_name = custom_name
        for mesh_name, shape_key_name in binds:
            _add_morph_target_bind(custom_expression, mesh_name, shape_key_name)
```

（`PRESET_EXPRESSION_MAPPING`が管理しない`lookUp`/`lookDown`への自動割り当てバインド（「上」「下」）は残す — desktop-vrm-mascotは使用せず、発火時のみ作用するため無害。設計書の改訂セクション参照）

- [ ] **Step 4: main処理に新ステップを配線する**

`prepare_ririka_kaihen_blend.py`の`if __name__ == "__main__":`ブロックの

```python
    hidden_default_outfit = hide_default_outfit_meshes()
    print(f"HIDDEN_DEFAULT_OUTFIT_MESHES: {len(hidden_default_outfit)}")

    relink_broken_textures()
```

を以下に置き換える:

```python
    hidden_default_outfit = hide_default_outfit_meshes()
    print(f"HIDDEN_DEFAULT_OUTFIT_MESHES: {len(hidden_default_outfit)}")

    hidden_mixed_in = hide_mixed_in_meshes()
    print(f"HIDDEN_MIXED_IN_MESHES: {len(hidden_mixed_in)}")

    relink_broken_textures()
```

- [ ] **Step 5: prepareを再実行してblendを再生成する**

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python "C:\Users\PC_User\Documents\ar-avatar-demo\scripts\prepare_ririka_kaihen_blend.py" -- "D:\VRChatCreatorCompanion\VRChatProjects\りりか　黒猫悪夢\Assets\ririka 黒猫悪夢(Clone).fbx" "C:\Users\PC_User\Documents\ar-avatar-demo\source\ririka_kaihen.blend"
```

Expected: 従来の出力（`HIPS_BONE_ADDED`〜`PHANTOM_EMISSION_FIXED`）に加えて`HIDDEN_MIXED_IN_MESHES: 3`が出力され、最後に`SAVED: ...ririka_kaihen.blend`。`RuntimeError`（メッシュ名が見つからない）が出た場合はリストのタイポを疑う。

- [ ] **Step 6: 一時ファイルを削除する**

削除対象（Task 1の残置ファイル）:
- `scripts/_audit_ririka_kaihen.py`
- `scripts/_render_single_mesh.py`
- `_audit_output.txt`
- `_expr_dump.txt`
- `_audit_renders\`（ディレクトリごと）

`del`/`Remove-Item`で個別に削除する（`rm -rf`は使わない。ディレクトリは`Remove-Item -Recurse _audit_renders -Confirm:$false`）。削除後に`git status --short`で、上記以外に意図しない変更がないことを確認する。

- [ ] **Step 7: commit**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add scripts/prepare_ririka_kaihen_blend.py scripts/export_vrm_ririka_kaihen.py
git commit -m "fix: 混入衣装メッシュの除外と表情バインド二重登録の解消"
```

---

### Task 2b: 【第2ラウンド改訂】口内パーツ（歯・舌）の物理削除

> **改訂の経緯（Task 3の1回目の検証で発覚）**: 衣装・羽の混入と表情バインド二重登録はTask 2で解消したが、「ピンクの開いた口」が残存した。追加調査で真因を特定: `Body`メッシュ（顔専用、シェイプキー705個）内の**歯（上下）・舌の3アイランド（計1568頂点、全て`body_LLC_Clone_`マテリアル）**が、幾何学的には唇の奥約9mmにあるにもかかわらず、`alphaMode=BLEND`+`doubleSided`のマテリアルをthree.jsが`depthWrite=false`で描画するため、プリミティブ内の描画順（歯→舌が顔スキンより後）で手前に合成されて見えていた。Unity側ではFXレイヤーが収納シェイプキー`t_upper_off`/`t_lower_off`/`tang_off`を常時1に保って口内ポケットへ収納していたが、blend内では全キー値0のため常時展開状態でエクスポートされていた。
>
> 修正方式は物理削除（案a）を採用。収納キーのvalue=1保存（案b）はエクスポータのウェイト出力とビューアのリセット挙動に依存して脆弱、マテリアル分離（案c）は歯・舌が顔スキンと同一スロットのため不可。削除の安全性は実機検証済み（削除後も他704キーのデルタは完全一致、レンダリングで顔・閉じ口とも正常、`vrc.v_aa`開口時も口内ポケット表示で自然）。

**Files:**
- Modify: `ar-avatar-demo/scripts/prepare_ririka_kaihen_blend.py`
- Delete: 第2ラウンド調査の残置一時ファイル（`scripts/_investigate_mouth_overlay.py`・`scripts/_verify_mouth_fix.py`・`scripts/_isolate_overlay_render.py`・`scripts/_isolate_tongue_render.py`・`_mouth_investigation\`）

- [ ] **Step 1: 口内パーツ削除関数を追加する**

`prepare_ririka_kaihen_blend.py`に、収納シェイプキーのデルタで対象頂点を特定して物理削除する関数を追加する（アイランド番号に依存しない頑健な特定方法）:

```python
# 実機検証（three-vrm）で発覚した「ピンクの開いた口」オーバーレイの修正:
# Bodyメッシュ内の歯（上下）・舌の3アイランドは、幾何学的には唇の奥約9mmに
# あるが、body_LLC_Clone_マテリアルがalphaMode=BLEND+doubleSidedでエクスポート
# されるため、three.js側でdepthWrite=falseの透過描画になり、プリミティブ内の
# 描画順（歯→舌が顔スキンより後）で手前に上書き合成されて見える。
# Unity/VRChat側ではFXレイヤーが収納シェイプキー（下記3キー）を常時1に保って
# 口内ポケットへ収納していたが、FBXにはキー値0で入ってくるため常時展開状態
# だった。収納キーvalue=1のまま保存する方式はエクスポータのウェイト出力と
# ビューア側のリセット挙動に依存して脆弱なため、該当頂点を物理削除する。
# 各キーのデルタは該当アイランドの頂点だけを排他的に動かす（他の頂点への
# 影響ゼロ、実機検証で確認済み）ため、デルタ非0の頂点集合＝削除対象になる。
MOUTH_STORAGE_SHAPE_KEYS = ["t_upper_off", "t_lower_off", "tang_off"]
MOUTH_PART_MESH_NAME = "Body"
EXPECTED_MOUTH_PART_VERTEX_COUNT = 1568  # 上歯569+下歯569+舌430（調査で実測）


def delete_mouth_storage_parts():
    """MOUTH_STORAGE_SHAPE_KEYSのデルタが非0の頂点（歯・舌のアイランド）を
    Bodyメッシュから物理削除する。"""
    import bmesh

    obj = bpy.data.objects.get(MOUTH_PART_MESH_NAME)
    if obj is None or obj.type != 'MESH':
        raise RuntimeError(f"メッシュオブジェクト'{MOUTH_PART_MESH_NAME}'が見つかりません")
    me = obj.data
    if me.shape_keys is None:
        raise RuntimeError(f"'{MOUTH_PART_MESH_NAME}'にシェイプキーがありません")

    key_blocks = me.shape_keys.key_blocks
    basis = key_blocks.get('Basis')
    if basis is None:
        raise RuntimeError("Basisシェイプキーが見つかりません")

    target_indices = set()
    for key_name in MOUTH_STORAGE_SHAPE_KEYS:
        kb = key_blocks.get(key_name)
        if kb is None:
            raise RuntimeError(f"収納シェイプキー'{key_name}'が見つかりません")
        for i in range(len(kb.data)):
            if (kb.data[i].co - basis.data[i].co).length > 1e-6:
                target_indices.add(i)

    if len(target_indices) != EXPECTED_MOUTH_PART_VERTEX_COUNT:
        raise RuntimeError(
            f"削除対象頂点数が想定と異なります: {len(target_indices)} != "
            f"{EXPECTED_MOUTH_PART_VERTEX_COUNT}（FBXの構造が変わった可能性。要再調査）"
        )

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    doomed = [bm.verts[i] for i in sorted(target_indices)]
    bmesh.ops.delete(bm, geom=doomed, context='VERTS')
    bm.to_mesh(me)
    bm.free()

    print(f"MOUTH_STORAGE_PARTS_DELETED: {len(target_indices)} vertices")
    return len(target_indices)
```

- [ ] **Step 2: main処理に配線する**

`hide_mixed_in_meshes()`呼び出しの直後（`relink_broken_textures()`の前）に追加:

```python
    delete_mouth_storage_parts()
```

- [ ] **Step 3: prepare再実行（Blender 4.5、`--factory-startup`推奨）→ 出力確認**

第2ラウンド調査の知見: ヘッドレス実行時にCATSアドオンのバックグラウンドスレッドがクラッシュすることがあるため`--factory-startup`を付ける（VRM Add-onはexport段でしか使わないためprepare段では問題ない）。

Expected: `MOUTH_STORAGE_PARTS_DELETED: 1568 vertices`を含む従来出力＋`SAVED:`。

- [ ] **Step 4: 一時ファイル削除（第2ラウンド調査の残置分）→ commit**

コミット対象は`scripts/prepare_ririka_kaihen_blend.py`のみ。メッセージ例: `fix: 口内パーツ(歯・舌)の収納シェイプキー対象頂点を物理削除`

---

### Task 3: VRM再エクスポート＋ブラウザ実機検証

**Files:** なし（コード変更なし、アーティファクト再生成と検証のみ）

- [ ] **Step 1: VRMを再エクスポートする**

```bash
"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --python "C:\Users\PC_User\Documents\ar-avatar-demo\scripts\export_vrm_ririka_kaihen.py" -- "C:\Users\PC_User\Documents\ar-avatar-demo\source\ririka_kaihen.blend" "C:\Users\PC_User\Documents\ar-avatar-demo\ririka_kaihen.vrm"
```

Expected: `MAPPING_DONE`に続いて`EXPORT_RESULT: {'FINISHED'}`。`RuntimeError`（シェイプキーが見つからない）が出た場合、`export_vrm_ririka_kaihen.py`の表情マッピングが参照するシェイプキーとblendの実態がズレている（Task 2の変更では起きないはずだが、起きたらBLOCKEDで報告）。

- [ ] **Step 2: プレビュー用にコピーしてブラウザで確認する**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
cp ririka_kaihen.vrm model.vrm
```

ブラウザツール（Browser paneの`preview_start { name: "ar-avatar-demo" }`）でHTTPサーバーを起動し、`http://localhost:8080/vrm-preview.html?t=<現在のUNIXタイム>`を開く（**キャッシュバスティング必須**）。

確認項目（それぞれスクリーンショットを取得する）:
1. **ニュートラル**: 口が閉じている・目に余計な模様がない・黒猫悪夢衣装のみ（別衣装の混入なし）・腰の羽なし・猫耳/肉球グローブ/黒レースドレス/黒レースソックスが揃っている
2. **5表情**: ページ上のボタンでhappy / relaxed / surprised / sad / cryingを順に発火し、それぞれ表情が変化すること（発火後は他の表情をリセットしてから次を確認する仕様になっている）

- [ ] **Step 3: リファレンスとの照合結果を報告する**

ニュートラルのスクリーンショットを前提知識セクションのリファレンス記述と照合し、一致/不一致を項目ごとに報告する。不一致（隠し漏れ・隠しすぎ・表情の異常）があれば、その内容を具体的に報告し、Task 2のリスト修正→再実行のループに戻る（オーケストレーターが差し戻しを判断する）。

---

### Task 4: desktop-vrm-mascot実環境確認（ユーザー目視承認ゲート）

**Files:** なし（アーティファクトのコピーと検証のみ）

- [ ] **Step 1: 新しいVRMをdesktop-vrm-mascotのdev用アバター置き場へコピーする**

```bash
cp "C:\Users\PC_User\Documents\ar-avatar-demo\ririka_kaihen.vrm" "C:\Users\PC_User\Documents\desktop-vrm-mascot\assets\dev-avatars\ririka_kaihen.vrm"
```

（desktop-vrm-mascotの`electron-store`設定（`%APPDATA%\desktop-vrm-mascot\config.json`の`vrmPath`）がこのパスを指していることを確認する。違うパスを指している場合はそのパスへコピーする）

- [ ] **Step 2: マスコットを起動して実環境確認する**

```bash
cd "C:\Users\PC_User\Documents\desktop-vrm-mascot"
npx electron-forge start -- --remote-debugging-port=9520
```

CDP経由（`http://localhost:9520/json/list`→`Runtime.evaluate`/`Page.captureScreenshot`、Node 24のネイティブ`WebSocket`）で:
1. ニュートラル（食事ループ中）のスクリーンショット → 口が閉じている・衣装が正しいこと
2. `window.__debugFlashExpression('happy')` → 表情変化のスクリーンショット
3. 同様に relaxed / surprised / sad / crying も1つずつ発火・撮影

確認後、起動した特定のelectronプロセスのみをPID指定で終了する（`taskkill /F /IM electron.exe`のような全体killはしない）。

- [ ] **Step 3: ユーザー目視承認（最終ゲート）**

Task 3・Task 4で取得したスクリーンショット（ブラウザのニュートラル＋5表情、マスコット実環境のニュートラル＋表情）をユーザーに提示し、リファレンスどおりになっているかの**目視承認を得る**。指摘があればTask 2のリスト修正へ差し戻す。承認が出たらこのプランは完了（このタスクにコミットはない。成果物のVRM/blendは従来どおりgit未追跡のまま）。
