#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ririka_kaihen.blend（Task 1で作成、Hipsボーン補完済み）からVRM 1.0形式で
ririka_kaihen.vrmを出力する。元の.blendファイルは一切変更しない。
"""
import sys
import bpy

ARMATURE_NAME = "Hips"
BODY_MESH_NAME = "Body"

# Task 3の目視確認で判明: angry/sadの単体シェイプキーは変位量が極めて小さく
# （実測 平均頂点変位: angry単体=0.005、sad単体=0.015、対してhappy単体=0.070・
# narrow=0.125）、レンダリングでほぼ無表情に見えるほど弱かった。また眉毛系の
# シェイプキー（brow_angry等）は前髪に隠れて視認できないため、目のシェイプ
# （narrow・eyelid_upper_tare・eyelid_lower_tare）と口のシェイプ（mouth_down）を
# 中心に構成を強化した。PRESET_EXPRESSION_MAPPINGは元の単一タプル構造では
# 複数シェイプキーを合成できないため、CUSTOM_EXPRESSION_MAPPINGと同じ
# リスト構造に統一した（apply_expression_mappingもそれに合わせて変更）。
PRESET_EXPRESSION_MAPPING = {
    "happy": [
        (BODY_MESH_NAME, "happy"),
        (BODY_MESH_NAME, "brow_smile"),
        (BODY_MESH_NAME, "mouth_smile"),
    ],
    "angry": [
        (BODY_MESH_NAME, "angry"),
        (BODY_MESH_NAME, "brow_angry"),
        (BODY_MESH_NAME, "narrow"),
    ],
    "sad": [
        (BODY_MESH_NAME, "sad"),
        (BODY_MESH_NAME, "mouth_down"),
        (BODY_MESH_NAME, "eyelid_upper_tare"),
        (BODY_MESH_NAME, "eyelid_lower_tare"),
        (BODY_MESH_NAME, "brow_down"),
    ],
    "relaxed": [(BODY_MESH_NAME, "nagomi")],
    "surprised": [(BODY_MESH_NAME, "びっくり")],
    "aa": [(BODY_MESH_NAME, "vrc.v_aa")],
    "ih": [(BODY_MESH_NAME, "vrc.v_ih")],
    "ou": [(BODY_MESH_NAME, "vrc.v_ou")],
    "ee": [(BODY_MESH_NAME, "vrc.v_e")],
    "oh": [(BODY_MESH_NAME, "vrc.v_oh")],
    "blink": [(BODY_MESH_NAME, "blink")],
    "blink_left": [(BODY_MESH_NAME, "blink_L")],
    "blink_right": [(BODY_MESH_NAME, "blink_R")],
}

CUSTOM_EXPRESSION_MAPPING = {
    "crying": [
        (BODY_MESH_NAME, "sad"),
        (BODY_MESH_NAME, "mouth_down"),
        (BODY_MESH_NAME, "eyelid_upper_tare"),
        (BODY_MESH_NAME, "eyelid_lower_tare"),
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
    "left_thumb_metacarpal": "Thumb_Proximal_L",
    "left_thumb_proximal": "Thumb_Intermediate_L",
    "left_thumb_distal": "Thumb_Distal_L",
    "right_thumb_metacarpal": "Thumb_Proximal_R",
    "right_thumb_proximal": "Thumb_Intermediate_R",
    "right_thumb_distal": "Thumb_Distal_R",
    "left_index_proximal": "Index_Proximal_L",
    "left_index_intermediate": "Index_Intermediate_L",
    "left_index_distal": "Index_Distal_L",
    "right_index_proximal": "Index_Proximal_R",
    "right_index_intermediate": "Index_Intermediate_R",
    "right_index_distal": "Index_Distal_R",
    "left_middle_proximal": "Middle_Proximal_L",
    "left_middle_intermediate": "Middle_Intermediate_L",
    "left_middle_distal": "Middle_Distal_L",
    "right_middle_proximal": "Middle_Proximal_R",
    "right_middle_intermediate": "Middle_Intermediate_R",
    "right_middle_distal": "Middle_Distal_R",
    "left_ring_proximal": "Ring_Proximal_L",
    "left_ring_intermediate": "Ring_Intermediate_L",
    "left_ring_distal": "Ring_Distal_L",
    "right_ring_proximal": "Ring_Proximal_R",
    "right_ring_intermediate": "Ring_Intermediate_R",
    "right_ring_distal": "Ring_Distal_R",
    "left_little_proximal": "Little_Proximal_L",
    "left_little_intermediate": "Little_Intermediate_L",
    "left_little_distal": "Little_Distal_L",
    "right_little_proximal": "Little_Proximal_R",
    "right_little_intermediate": "Little_Intermediate_R",
    "right_little_distal": "Little_Distal_R",
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

    for preset_name, binds in PRESET_EXPRESSION_MAPPING.items():
        expression = getattr(expressions.preset, preset_name)
        for mesh_name, shape_key_name in binds:
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
