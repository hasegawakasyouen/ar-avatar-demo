#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Mixamo変換済みFBXアニメーションを、リリカのArmature（VRM Humanoidマッピング済み）へ
Copy Rotationコンストレイントでリターゲティングし、VRMA形式でエクスポートする。
出力されるVRMAはVRM Humanoid空間に正規化されているため、アバターを問わず再利用できる。
元の.blendファイルは一切変更しない（save_mainfileを呼ばない）。
"""
import os
import sys
import bpy

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
from export_vrm import ARMATURE_NAME, apply_bone_mapping, open_source_file, get_armature_object

# Mixamoボーン名 -> リリカ側のArmatureボーン名（スパイク検証済み、指は対象外）
RETARGET_MAP = {
    "mixamorig:Hips": "Hips",
    "mixamorig:Spine": "Spine",
    "mixamorig:Spine2": "Chest",
    "mixamorig:Neck": "Neck",
    "mixamorig:Head": "Head",
    "mixamorig:LeftShoulder": "sholder_L",
    "mixamorig:LeftArm": "Upperarm_L",
    "mixamorig:LeftForeArm": "Lowerarm_L",
    "mixamorig:LeftHand": "Left Hand",
    "mixamorig:RightShoulder": "sholder_R",
    "mixamorig:RightArm": "Upperarm_R",
    "mixamorig:RightForeArm": "Lowerarm_R",
    "mixamorig:RightHand": "Right Hand",
    "mixamorig:LeftUpLeg": "Upperleg_L",
    "mixamorig:LeftLeg": "Lowerleg_L",
    "mixamorig:LeftFoot": "Foot_L",
    "mixamorig:RightUpLeg": "Upperleg_R",
    "mixamorig:RightLeg": "Lowerleg_R",
    "mixamorig:RightFoot": "Foot_R",
}


def get_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python export_vrma.py -- "
            "<ririka_blend> <mixamo_fbx> <output_vrma>"
        )
    return argv[argv.index("--") + 1:]


def parse_args(args):
    if len(args) != 3:
        raise SystemExit(
            "Expected 3 positional args: <ririka_blend> <mixamo_fbx> <output_vrma>"
        )
    return args[0], args[1], args[2]


def import_mixamo_animation(mixamo_fbx):
    objects_before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.fbx(filepath=mixamo_fbx)
    objects_after = set(bpy.data.objects.keys())
    new_object_names = objects_after - objects_before

    new_armatures = [
        bpy.data.objects[name]
        for name in new_object_names
        if bpy.data.objects[name].type == 'ARMATURE'
    ]
    if len(new_armatures) != 1:
        raise RuntimeError(
            f"'{mixamo_fbx}'のインポートで新規Armatureが{len(new_armatures)}個見つかりました"
            f"（1個であるべき）: {[a.name for a in new_armatures]}"
        )
    return new_armatures[0]


def set_frame_range_from_action(mixamo_armature):
    if mixamo_armature.animation_data is None or mixamo_armature.animation_data.action is None:
        raise RuntimeError("Mixamoアーマチュアにアニメーションアクションがありません")
    action = mixamo_armature.animation_data.action
    start, end = action.frame_range
    scene = bpy.context.scene
    scene.frame_start = int(start)
    scene.frame_end = int(end)


def apply_retarget_constraints(ririka_armature, mixamo_armature):
    missing = []
    for mixamo_bone, ririka_bone in RETARGET_MAP.items():
        if mixamo_bone not in mixamo_armature.pose.bones:
            missing.append(("mixamo missing", mixamo_bone))
            continue
        if ririka_bone not in ririka_armature.pose.bones:
            missing.append(("ririka missing", ririka_bone))
            continue
        pb = ririka_armature.pose.bones[ririka_bone]
        con = pb.constraints.new('COPY_ROTATION')
        con.name = "VRMA_RETARGET"
        con.target = mixamo_armature
        con.subtarget = mixamo_bone
        con.target_space = 'WORLD'
        con.owner_space = 'WORLD'
    if missing:
        raise RuntimeError(f"以下のボーンが見つかりません: {missing}")


def bake_retarget_animation(ririka_armature, frame_start, frame_end):
    """Copy Rotationコンストレイントで駆動されているポーズを、
    ririka_armature自身の実キーフレームへベイクする。
    VRMAエクスポータ(vrm_animation_exporter.py)はarmature自身の
    animation_data.actionしか読まず、他オブジェクトを指すコンストレイントは
    一切評価しないため、このベイクなしではモーションデータが0件のまま出力される。
    """
    bpy.context.view_layer.objects.active = ririka_armature
    ririka_armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='DESELECT')
    for ririka_bone_name in RETARGET_MAP.values():
        pb = ririka_armature.pose.bones.get(ririka_bone_name)
        if pb:
            pb.select = True
    bpy.ops.nla.bake(
        frame_start=frame_start,
        frame_end=frame_end,
        only_selected=True,
        visual_keying=True,
        clear_constraints=True,
        clear_parents=False,
        use_current_action=False,
        bake_types={'POSE'},
    )
    bpy.ops.object.mode_set(mode='OBJECT')


if __name__ == "__main__":
    ririka_blend, mixamo_fbx, output_vrma = parse_args(get_args())

    open_source_file(ririka_blend)
    ririka_armature = get_armature_object()
    apply_bone_mapping(ririka_armature)
    mixamo_armature = import_mixamo_animation(mixamo_fbx)
    set_frame_range_from_action(mixamo_armature)
    apply_retarget_constraints(ririka_armature, mixamo_armature)
    bake_retarget_animation(ririka_armature, bpy.context.scene.frame_start, bpy.context.scene.frame_end)
    print("RETARGET_SETUP_DONE")

    result = bpy.ops.export_scene.vrma(
        filepath=output_vrma,
        armature_object_name=ARMATURE_NAME,
    )
    print(f"EXPORT_RESULT: {result}")
    if result != {'FINISHED'}:
        raise RuntimeError(f"VRMAエクスポートが失敗しました: {result}")
