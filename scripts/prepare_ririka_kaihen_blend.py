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
