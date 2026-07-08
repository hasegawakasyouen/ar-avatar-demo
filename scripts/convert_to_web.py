# scripts/convert_to_web.py
import bpy
import sys


def get_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python convert_to_web.py "
            "-- <input_fbx|--smoketest> <output_glb> <output_usdz> [extra_anim_fbx...]"
        )
    return argv[argv.index("--") + 1:]


def harvest_extra_animations(extra_anim_paths):
    for anim_path in extra_anim_paths:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=anim_path)
        imported = [o for o in bpy.data.objects if o not in before]
        armature = next((o for o in imported if o.type == 'ARMATURE'), None)
        if armature and armature.animation_data and armature.animation_data.action:
            armature.animation_data.action.use_fake_user = True
        for obj in imported:
            bpy.data.objects.remove(obj, do_unlink=True)


def export_glb_and_usdz(output_glb, output_usdz):
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        export_animations=True,
        export_animation_mode='ACTIONS',
    )
    bpy.ops.wm.usd_export(
        filepath=output_usdz,
        export_animation=True,
    )


def main():
    args = get_args()
    if len(args) < 3:
        raise SystemExit(
            "Expected at least 3 args: <input_fbx|--smoketest> <output_glb> <output_usdz> [extra_anim_fbx...]"
        )
    mode, output_glb, output_usdz = args[0], args[1], args[2]
    extra_anim_paths = args[3:]

    if mode == "--smoketest":
        # Blenderの初期シーン(Cube/Light/Camera)をそのまま使う
        bpy.ops.wm.read_factory_settings(use_empty=False)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=mode)

    if extra_anim_paths:
        harvest_extra_animations(extra_anim_paths)

    export_glb_and_usdz(output_glb, output_usdz)
    print("CONVERT_OK", output_glb, output_usdz)


main()
