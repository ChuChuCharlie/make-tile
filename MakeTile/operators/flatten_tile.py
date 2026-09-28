import bpy
from .. lib.utils.collections import get_objects_owning_collections


class MT_OT_Flatten_Tile(bpy.types.Operator):
    """Applies all modifiers to the selected objects and
    any other objects in the same collection then deletes any
    meshes in the objects' owning collection(s) that are not visible"""

    bl_idname = "object.flatten_tiles"
    bl_label = "Flatten Tiles"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.mode == 'OBJECT' and obj.mt_object_props.is_mt_object is True

    def execute(self, context):
        selected_objects = context.selected_objects
        tile_collections = set()

        # Save selected object's owning collection(s)
        for obj in selected_objects:
            if obj.type == 'MESH':
                obj_collections = get_objects_owning_collections(obj.name)
                for collection in obj_collections:
                    tile_collections.add(collection)

        for collection in tile_collections:
            flatten_tile(context, collection)
        return {'FINISHED'}

def flatten_tile(context, collection):
    collection_objects = list(collection.all_objects)
    if not collection_objects:
        return None

    # save a list of meshes
    meshes = []
    for obj in collection_objects:
        if obj.type == 'MESH':
            meshes.append(obj.data)

    # Unparent the objects in this collection while preserving world transforms.
    for obj in collection_objects:
        if obj.parent:
            matrix_world = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = matrix_world

    # get all visible mesh objects
    visible_mesh_objects = [obj for obj in collection.all_objects if obj.type == 'MESH' and obj.visible_get() is True]

    if not visible_mesh_objects:
        return None

    # apply all modifiers
    depsgraph = context.evaluated_depsgraph_get()

    for obj in visible_mesh_objects:
        object_eval = obj.evaluated_get(depsgraph)
        mesh_from_eval = bpy.data.meshes.new_from_object(object_eval)
        obj.modifiers.clear()
        obj.data = mesh_from_eval

    # Remember which object to keep; object references become invalid after join.
    keep_name = visible_mesh_objects[0].name

    # join all objects
    if len(visible_mesh_objects) > 1:
        with bpy.context.temp_override(object=visible_mesh_objects[0], active_object=visible_mesh_objects[0], selected_objects=visible_mesh_objects, selected_editable_objects=visible_mesh_objects):
            bpy.ops.object.join()

    # Delete all other objects in collection. Snapshot names first so we are
    # not modifying the collection while iterating it.
    object_names = [o.name for o in collection.all_objects]
    for obj_name in object_names:
        if obj_name != keep_name and obj_name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[obj_name], do_unlink=True)

    # Delete all unused meshes in collection. Deduplicate because shared
    # mesh datablocks would be freed on the first remove() and raise on the
    # second iteration. Blender returns the same Python wrapper for a given
    # datablock during the process lifetime, so id(mesh) is safe here.
    seen = set()
    for mesh in meshes:
        if mesh is not None and id(mesh) not in seen:
            seen.add(id(mesh))
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)

    # Rename kept object to collection name
    if keep_name in bpy.data.objects:
        obj = bpy.data.objects[keep_name]
        obj.name = collection.name

        obj.mt_object_props.geometry_type = 'FLATTENED'
        obj.mt_object_props.is_displacement = False

        return obj

    return None
