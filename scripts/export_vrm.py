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
