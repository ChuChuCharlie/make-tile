import time
import bpy
import bmesh
import addon_utils
from bpy.types import Panel
from .. lib.utils.collections import get_objects_owning_collections

class MT_PT_Voxelise_Panel(Panel):
    bl_order = 9
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Make Tile"
    bl_idname = "MT_PT_Voxelise_Panel"
    bl_label = "Voxelise Settings"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type in {'MESH'}

    def draw(self, context):
        scene = context.scene
        scene_props = scene.mt_scene_props
        layout = self.layout

        layout.operator('scene.mt_voxelise_objects', text='Voxelise Objects')
        layout.prop(scene_props, 'voxel_size')
        layout.prop(scene_props, 'voxel_adaptivity')
        layout.prop(scene_props, 'voxel_merge')
        layout.prop(scene_props, 'fix_non_manifold')

class MT_OT_Object_Voxeliser(bpy.types.Operator):
    """Applies all modifiers to the selected objects and, optionally merges them
    and then voxelises objects"""
    bl_idname = "scene.mt_voxelise_objects"
    bl_label = "Voxelise Objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.mode == 'OBJECT'

    def execute(self, context):
        scene_props = context.scene.mt_scene_props
        merge = scene_props.voxel_merge
        selected_objects = [obj for obj in context.selected_editable_objects if obj.type == 'MESH']
        meshes = []

        depsgraph = context.evaluated_depsgraph_get()

        for obj in selected_objects:
            if context.object.type == 'MESH':
                meshes.append(obj.data)
                # low level version of apply all modifiers
                object_eval = obj.evaluated_get(depsgraph)
                mesh_from_eval = bpy.data.meshes.new_from_object(object_eval)
                obj.modifiers.clear()
                obj.data = mesh_from_eval

        if merge is True:
            with bpy.context.temp_override(selected_objects=selected_objects,selected_editable_objects=selected_objects,object=context.active_object,active_object=context.active_object):
                bpy.ops.object.join()

        selected_objects = [obj for obj in context.selected_editable_objects if obj.type == 'MESH']

        for obj in selected_objects:
            voxelise(context, obj)
            if scene_props.fix_non_manifold:
                make_manifold(context, obj)

        for mesh in bpy.data.meshes:
            if mesh is not None:
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)

        return {'FINISHED'}


def voxelise(context, obj):
    """Voxelise the passed in object.

    Args:
        obj (bpy.types.Object): object to be voxelised
    """
    props = context.scene.mt_scene_props
    obj.data.remesh_voxel_size = props.voxel_size
    obj.data.remesh_voxel_adaptivity = props.voxel_adaptivity

    with bpy.context.temp_override(object=obj,active_object=obj,selected_objects=[obj],selected_editable_objects=[obj]):
        bpy.ops.object.voxel_remesh()
    obj.mt_object_props.geometry_type = 'VOXELISED'


def count_non_manifold_edges(obj):
    """Return the number of non-watertight edges in the object's mesh.

    An edge is treated as non-manifold if it is not linked to exactly two faces
    (boundary, wire, or shared by three or more faces).

    Args:
        obj (bpy.types.Object): mesh object

    Returns:
        int: number of non-manifold edges
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    non_manifold = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    bm.free()
    return non_manifold


def ensure_print3d_addon():
    """Enable Blender's built-in 3D-Print Toolbox if available.

    Returns:
        bool: True if the addon is loaded and enabled, else False
    """
    loaded, enabled = addon_utils.check("object_print3d_utils")
    if loaded and enabled:
        return True

    try:
        addon_utils.enable("object_print3d_utils", default_set=True)
    except Exception:
        return False

    loaded, enabled = addon_utils.check("object_print3d_utils")
    return loaded and enabled


def make_manifold(context, obj, report=None):
    """Make the passed in object manifold using the 3dPrint toolkit addon

    Falls back to a bounded ``bpy.ops.mesh.fill_holes`` loop when the 3D-Print
    Toolbox is unavailable.

    Args:
        context (bpy.context): context
        obj (bpy.types.Object): object
        report (callable, optional): operator report method for warnings
    """
    non_manifold = count_non_manifold_edges(obj)
    if non_manifold == 0:
        return

    # Ensure this object is the active one so mesh operators operate on it.
    context.view_layer.objects.active = obj

    if ensure_print3d_addon():
        with bpy.context.temp_override(
                object=obj,
                active_object=obj,
                selected_objects=[obj],
                selected_editable_objects=[obj],
                edit_object=obj):
            bpy.ops.mesh.print3d_clean_non_manifold(threshold=0.0001, sides=0)

        non_manifold = count_non_manifold_edges(obj)
        if non_manifold > 0 and report:
            report(
                {'WARNING'},
                f"{obj.name}: {non_manifold} non-manifold edges remain after cleanup")
        return

    # Fallback: run fill_holes repeatedly with a time/iteration guard.
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    timeout = 30  # seconds
    max_iterations = 10
    start_time = time.time()

    for _ in range(max_iterations):
        if time.time() - start_time > timeout:
            if report:
                report(
                    {'WARNING'},
                    f"{obj.name}: make_manifold timed out after {timeout}s with {non_manifold} non-manifold edges remaining")
            break

        with bpy.context.temp_override(
                object=obj,
                active_object=obj,
                selected_objects=[obj],
                selected_editable_objects=[obj],
                edit_object=obj):
            bpy.ops.mesh.fill_holes(sides=0)

        non_manifold = count_non_manifold_edges(obj)
        if non_manifold == 0:
            break

    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
