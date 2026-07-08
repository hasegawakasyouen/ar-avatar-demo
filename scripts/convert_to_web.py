# scripts/convert_to_web.py
import bpy
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEXTURES_DIR = os.path.join(SCRIPT_DIR, "..", "textures")

# source/avatar_idle_mixamo.fbx はUnityから出力された絶対パス(Z:\Blender\...)を
# 参照するダングリングなテクスチャノードしか持たない（詳細はREADME Step 4参照）。
# ここで textures/ 配下の実PNGへ強制的に張り替える。マテリアル名 -> テクスチャファイル名。
# body_option は独自テクスチャを持たず、bodyと同じ画像を共有する（過去の調査で判明済み、
# コミット f4d2067 参照）。
MATERIAL_TEXTURE_MAP = {
    "body": "body.png",
    "body_b": "body_b.png",
    "body_option": "body.png",
    "cloth": "Cloth.png",
    "cloth1": "cloth1.png",
    "Hair": "Hair.png",
    "underwear": "underwear.png",
    "metal": "cloth2.png",
}


def get_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python convert_to_web.py "
            "-- <input_fbx|--smoketest> <output_glb> <output_usdz> [extra_anim_fbx...]"
        )
    return argv[argv.index("--") + 1:]


def relink_material_textures(textures_dir):
    for mat_name, tex_filename in MATERIAL_TEXTURE_MAP.items():
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            continue

        mat.use_nodes = True
        node_tree = mat.node_tree
        bsdf = next(
            (n for n in node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None
        )
        if bsdf is None:
            continue

        base_color_input = bsdf.inputs["Base Color"]
        alpha_input = bsdf.inputs["Alpha"]

        # 既存の（壊れたPSDパス等を指す）Image Textureノードをすべて取り除く
        for socket in (base_color_input, alpha_input):
            for link in list(socket.links):
                src_node = link.from_node
                node_tree.links.remove(link)
                if src_node.type == "TEX_IMAGE":
                    node_tree.nodes.remove(src_node)

        tex_path = os.path.join(textures_dir, tex_filename)
        image = bpy.data.images.load(tex_path, check_existing=True)

        tex_node = node_tree.nodes.new("ShaderNodeTexImage")
        tex_node.image = image
        node_tree.links.new(tex_node.outputs["Color"], base_color_input)

        # PNGのアルファチャンネルが半透明・ゴースト化を引き起こした過去の回帰
        # (0ea6721 / 8ccfcb7) を避けるため、Alphaには接続せず不透明を明示する。
        alpha_input.default_value = 1.0
        mat.blend_method = "OPAQUE"


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
        relink_material_textures(TEXTURES_DIR)

    if extra_anim_paths:
        harvest_extra_animations(extra_anim_paths)

    export_glb_and_usdz(output_glb, output_usdz)
    print("CONVERT_OK", output_glb, output_usdz)


main()
