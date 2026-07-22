#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export a reduced VRM 1.0 asset for the iOS mascot spike.

The source .blend is opened without being saved. The exporter keeps only shape
keys referenced by the mascot's VRM expressions and downsizes oversized images
in memory before delegating the VRM metadata/export work to the established
Ririka Kaihen exporter.
"""

import sys

import bpy

import export_vrm_ririka_kaihen as base


DEFAULT_MAX_TEXTURE_SIZE = 1024


def parse_args(argv):
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python "
            "scripts/export_vrm_ririka_kaihen_ios.py -- "
            "<source_blend> <output_vrm> [max_texture_size]"
        )
    args = argv[argv.index("--") + 1 :]
    if len(args) not in (2, 3):
        raise SystemExit(
            "Expected <source_blend> <output_vrm> [max_texture_size]"
        )
    max_texture_size = int(args[2]) if len(args) == 3 else DEFAULT_MAX_TEXTURE_SIZE
    if max_texture_size < 256:
        raise SystemExit("max_texture_size must be at least 256")
    return args[0], args[1], max_texture_size


def required_shape_keys_by_mesh():
    required = {}
    mappings = list(base.PRESET_EXPRESSION_MAPPING.values())
    mappings.extend(base.CUSTOM_EXPRESSION_MAPPING.values())
    for binds in mappings:
        for mesh_name, shape_key_name in binds:
            required.setdefault(mesh_name, set()).add(shape_key_name)
    return required


def prune_shape_keys():
    required_by_mesh = required_shape_keys_by_mesh()
    removed = 0
    kept = 0

    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.data.shape_keys is None:
            continue
        required = required_by_mesh.get(obj.name, set())
        key_blocks = obj.data.shape_keys.key_blocks
        missing = sorted(name for name in required if name not in key_blocks)
        if missing:
            raise RuntimeError(f"{obj.name} is missing required shape keys: {missing}")

        for key_block in list(key_blocks)[1:][::-1]:
            if key_block.name in required:
                kept += 1
                continue
            obj.shape_key_remove(key_block)
            removed += 1

    print(f"IOS_SHAPE_KEYS: kept={kept} removed={removed}")


def resize_images(max_texture_size):
    resized = 0
    for image in bpy.data.images:
        width, height = image.size
        if width <= 0 or height <= 0 or max(width, height) <= max_texture_size:
            continue
        scale = max_texture_size / max(width, height)
        target_width = max(1, round(width * scale))
        target_height = max(1, round(height * scale))
        image.scale(target_width, target_height)
        # Pack the changed pixels so the VRM exporter does not reuse the
        # original oversized file referenced by image.filepath.
        image.pack(as_png=True)
        resized += 1
        print(
            f"IOS_TEXTURE: {image.name} {width}x{height} -> "
            f"{target_width}x{target_height}"
        )
    print(f"IOS_TEXTURES: resized={resized} max={max_texture_size}")


def export(source_blend, output_vrm, max_texture_size):
    bpy.ops.wm.open_mainfile(filepath=source_blend)
    prune_shape_keys()
    resize_images(max_texture_size)

    armature_object = base.get_armature_object()
    base.apply_bone_mapping(armature_object)
    base.apply_expression_mapping(armature_object)
    base.apply_meta(armature_object)

    result = bpy.ops.export_scene.vrm(
        filepath=output_vrm,
        armature_object_name=base.ARMATURE_NAME,
        ignore_warning=True,
        enable_advanced_preferences=True,
        export_try_sparse_sk=True,
    )
    print(f"EXPORT_RESULT: {result}")
    if result != {"FINISHED"}:
        raise RuntimeError(f"VRM export failed: {result}")


if __name__ == "__main__":
    export(*parse_args(sys.argv))
