#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""「りりか 黒猫悪夢」のFBXをインポートし、単体で存在しないHipsボーンを
Armatureオブジェクトのローカル原点（実測でワールドZ=0.7251m、想定される腰の高さと一致）に
新規追加してSpine/Upperleg_L/Upperleg_Rを再ペアレントしたうえで、
作業用.blendとして保存する。元のFBX/Unityプロジェクトは一切変更しない。

Task 4のブラウザ実機検証で発覚したバグの修正:
すべてのメッシュがArmatureオブジェクト（このFBXでは"Hips"という名前）に
オブジェクトペアレント（parent_type='OBJECT'、Armatureモディファイアと併用）
されている。この状態でVRM Add-on（io_scene_gltf2ベース）がエクスポートすると、
メッシュノードがルートボーン"Hips"ノードの子としてグラフ上にネストされる一方、
スキニング用のbindMatrixは「メッシュはシーンルート相対でほぼ単位行列の位置にある」
という前提で計算される。実機検証（three-vrm）で確認した通り、結果として
bindMatrix=単位行列だがmatrixWorld=[0, 0.7251, 0.0244]（Hipsの実ワールド座標を
ノード階層経由で継承）という不一致が生じ、メッシュが崩壊して見える。

最初に「Armatureオブジェクト自身のワールド変換（Z=0.7251m等のオフセット）を
bpy.ops.object.transform_applyでボーンのレスト位置へ焼き込む」という対策を
単独で試したが、オフセットが物理的にHipsボーンのワールド座標として必ず
残る以上、ノード階層上でメッシュがHipsの子である限り同じ不一致が再現し、
効果がないことを実機検証で確認した（bindMatrix/matrixWorldとも変化なし）。

真因はメッシュがArmatureオブジェクトにオブジェクトペアレントされている
ことそのもの（エクスポータがこれを見てメッシュノードをルートボーンの子に
ネストする）。そのため、Hipsボーン追加後に対象メッシュのオブジェクトペアレントを
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')で解除する
（ワールド座標は維持したまま親子関係のみ外す）。Armatureモディファイアは
オブジェクト参照のみで機能し親子関係に依存しないため、非破壊スキニングは
維持される。これによりエクスポート後のメッシュノードはHipsの子ではなく
シーンルート直下の独立ノード（skinのみで変形）になり、二重変形が解消される
ことを実機検証で確認済み。

Armatureオブジェクト自身の変形も単位行列へ適用する（transform_apply）。
単独では上記バグを解決しないが、Blender公式が推奨するglTFエクスポート前の
一般的なベストプラクティスであり、メッシュのmatrix_parent_inverseを
Blenderが自動調整するため副作用もない。
"""
import math
import sys

import bpy
import mathutils

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


def apply_armature_transform(armature_object):
    """Armatureオブジェクト自身のワールド変換（location/rotation/scale）を
    単位行列へ適用し、オフセットをボーンのレスト位置に焼き込む。
    メッシュはArmatureオブジェクトにオブジェクトペアレントされているが、
    Blenderのtransform_applyは子のmatrix_parent_inverseを自動調整するため
    メッシュのワールド座標・Hipsボーンのワールド座標は変化しない。
    """
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = armature_object
    armature_object.select_set(True)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    loc, rot, scale = armature_object.matrix_world.decompose()
    if loc.length > 1e-4:
        raise RuntimeError(
            f"Armatureオブジェクトのワールド平行移動が単位行列化されていません: {loc}"
        )


def unparent_skinned_meshes(armature_object):
    """Armatureオブジェクトにオブジェクトペアレントされている（かつ
    Armatureモディファイアで実際にスキニングされている）メッシュの
    オブジェクトペアレントを、ワールド座標を保ったまま解除する。
    VRMエクスポート時にメッシュノードがルートボーン("Hips")ノードの子として
    誤ってネストされ、bindMatrix（スキニング側の想定）とmatrixWorld
    （ノード階層継承）が食い違う二重変形バグを防ぐための処理。
    Armatureモディファイアはオブジェクト参照のみで機能するため、
    親子関係を外してもスキニングそのものは維持される。
    """
    targets = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.parent is not armature_object:
            continue
        if any(m.type == 'ARMATURE' and m.object == armature_object for m in obj.modifiers):
            targets.append(obj)

    if not targets:
        raise RuntimeError(
            "Armatureにオブジェクトペアレントされたスキンメッシュが見つかりません。想定外の状態です"
        )

    bpy.ops.object.select_all(action='DESELECT')
    for obj in targets:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = targets[0]
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    still_parented = [obj.name for obj in targets if obj.parent is not None]
    if still_parented:
        raise RuntimeError(f"ペアレント解除に失敗したメッシュがあります: {still_parented}")

    # parent_clear(KEEP_TRANSFORM)は、外れた親（Armature）が持っていた
    # ワールド変換（このFBXでは回転90°+スケール0.01。親の0.01スケール[Empty]と
    # Armatureオブジェクト自身の回転を合成したもの）を、ワールド座標を
    # 保つためにメッシュ自身のオブジェクト変換（location/rotation/scale）に
    # そのまま転記する。
    #
    # ここで単純にこの変形を単位行列へtransform_applyするだけでは不十分だった
    # （実機検証で確認済み: 実際に試したがエクスポート結果は一切変化しなかった。
    # transform_applyはワールド座標を保存する操作である以上、当然の結果）。
    #
    # 真因はVRM Add-on（io_scene_gltf2ベース）のエクスポータが、Armatureに
    # オブジェクトペアレントされたボーン階層（Hipsボーン等）には固有の変換経路を
    # 使う一方、Armatureの子から外れた単体メッシュオブジェクトには標準の
    # 「Blender Z-up → glTF Y-up」座標軸変換（(x,y,z)→(x,z,-y)相当）を別途
    # 適用すること。このFBXはボーン側が既にY軸を上方向として一貫している
    # （実機検証: 正しいボーン階層はこの変換を受けずにそのまま出力される）ため、
    # ペアレントを外した単体メッシュに標準変換が適用されると軸が入れ替わり、
    # 頭部メッシュ等が本来の高さ(y≈1.03〜1.19)ではなくz≈-1.0〜-1.23という
    # 無関係な位置に描画されることを実機検証（three-vrm、Tailメッシュの座標を
    # 使い軸入れ替え式(x,y,z)→(x,z,-y)と厳密に一致することを確認）で特定した。
    #
    # 対策として、エクスポータが適用するこの変換を打ち消す補正回転
    # （X軸まわり+90°、上記変換の逆行列）を各メッシュのワールド変形に
    # あらかじめ合成してから単位行列へtransform_applyし、頂点データへ
    # 焼き込む。これによりBlender内の見た目上の整合性（メッシュの向き）は
    # 崩れるが、この.blendはインタラクティブ編集用ではなくVRMエクスポート
    # 専用の作業ファイルであるため許容する。エクスポート後の結果が正しい
    # ワールド座標（ボーン階層と一致する座標系）になることを実機検証で確認済み。
    axis_conversion_compensation = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
    for obj in targets:
        obj.matrix_world = axis_conversion_compensation @ obj.matrix_world

    bpy.ops.object.select_all(action='DESELECT')
    for obj in targets:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = targets[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    not_identity = []
    for obj in targets:
        loc, rot, scale = obj.matrix_world.decompose()
        if loc.length > 1e-4 or abs(rot.angle) > 1e-4 or (scale - scale.__class__((1, 1, 1))).length > 1e-4:
            not_identity.append(obj.name)
    if not_identity:
        raise RuntimeError(f"メッシュの変形が単位行列化されていません: {not_identity}")

    return targets


if __name__ == "__main__":
    source_fbx, output_blend = parse_args(get_args())

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=source_fbx)

    armature_object = bpy.data.objects.get(ARMATURE_NAME)
    if armature_object is None or armature_object.type != 'ARMATURE':
        raise RuntimeError(f"Armatureオブジェクト'{ARMATURE_NAME}'が見つかりません")

    add_hips_bone(armature_object)
    print("HIPS_BONE_ADDED")

    apply_armature_transform(armature_object)
    print("ARMATURE_TRANSFORM_APPLIED")

    unparented = unparent_skinned_meshes(armature_object)
    print(f"UNPARENTED_SKINNED_MESHES: {len(unparented)}")

    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    print(f"SAVED: {output_blend}")
