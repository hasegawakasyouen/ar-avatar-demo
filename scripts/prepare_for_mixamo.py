# scripts/prepare_for_mixamo.py
import bpy
import sys

DECIMATE_THRESHOLD = 30000  # このトライアングル数を超えたらデシメート
DECIMATE_TARGET = 25000     # デシメート後の目標トライアングル数


def get_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python prepare_for_mixamo.py "
            "-- <input_fbx> <output_fbx>"
        )
    return argv[argv.index("--") + 1:]


def count_triangles(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def remove_shape_keys(mesh_objs):
    for obj in mesh_objs:
        while obj.data.shape_keys and obj.data.shape_keys.key_blocks:
            obj.shape_key_remove(obj.data.shape_keys.key_blocks[0])


def join_meshes(mesh_objs):
    if len(mesh_objs) == 1:
        return mesh_objs[0]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def decimate_if_needed(mesh_obj):
    tris = count_triangles(mesh_obj)
    if tris <= DECIMATE_THRESHOLD:
        print(f"PREPARE_INFO triangles={tris} <= threshold={DECIMATE_THRESHOLD}, skipping decimate")
        return
    ratio = DECIMATE_TARGET / tris
    mod = mesh_obj.modifiers.new(name="Decimate", type='DECIMATE')
    mod.ratio = ratio
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    print(f"PREPARE_INFO decimated from {tris} to ~{count_triangles(mesh_obj)} triangles")


def strip_armature(mesh_objs):
    for obj in mesh_objs:
        for mod in list(obj.modifiers):
            if mod.type == 'ARMATURE':
                obj.modifiers.remove(mod)
        if obj.parent and obj.parent.type == 'ARMATURE':
            matrix_world = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = matrix_world

    for obj in list(bpy.data.objects):
        if obj.type == 'ARMATURE':
            bpy.data.objects.remove(obj, do_unlink=True)


def main():
    args = get_args()
    if len(args) != 2:
        raise SystemExit("Expected 2 args: <input_fbx> <output_fbx>")
    input_fbx, output_fbx = args

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=input_fbx)

    mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']

    remove_shape_keys(mesh_objs)
    joined = join_meshes(mesh_objs)
    decimate_if_needed(joined)
    strip_armature([joined])

    bpy.ops.export_scene.fbx(filepath=output_fbx, use_selection=False, add_leaf_bones=False)
    print("PREPARE_OK", output_fbx)


main()
