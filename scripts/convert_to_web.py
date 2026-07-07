# scripts/convert_to_web.py
import bpy
import sys


def get_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python convert_to_web.py "
            "-- <input_fbx|--smoketest> <output_glb> <output_usdz>"
        )
    return argv[argv.index("--") + 1:]


def export_glb_and_usdz(output_glb, output_usdz):
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        export_animations=True,
    )
    bpy.ops.wm.usd_export(
        filepath=output_usdz,
        export_animation=True,
    )


def main():
    args = get_args()
    if len(args) != 3:
        raise SystemExit(
            "Expected 3 args: <input_fbx|--smoketest> <output_glb> <output_usdz>"
        )
    mode, output_glb, output_usdz = args

    if mode == "--smoketest":
        # Blenderの初期シーン(Cube/Light/Camera)をそのまま使う
        bpy.ops.wm.read_factory_settings(use_empty=False)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=mode)

    export_glb_and_usdz(output_glb, output_usdz)
    print("CONVERT_OK", output_glb, output_usdz)


main()
