import os
import textwrap
from random import random
import bpy
import addon_utils
from bpy.types import Panel
from bpy.props import BoolProperty, StringProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper
from .. utils.registration import get_prefs
from .voxeliser import voxelise, make_manifold
from .decimator import decimate
from .. lib.utils.collections import get_objects_owning_collections
from . bakedisplacement import (
    set_cycles_to_bake_mode,
    reset_renderer_from_bake,
    bake_displacement_map)
from . return_to_preview import set_to_preview
from ..enums.enums import units

# TODO: Currently if you select an architectural element rather than a tile the exporter fails.
class MT_PT_Export_Panel(Panel):
    bl_order = 50
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Make Tile"
    bl_idname = "MT_PT_Export_Panel"
    bl_label = "Export"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type in {'MESH'}

    def draw(self, context):
        scene = context.scene
        scene_props = scene.mt_scene_props
        obj = context.object
        prefs = get_prefs()

        char_width = 9  # TODO find a way of actually getting this rather than guessing
        print_tools_txt = "For more options please enable the 3D print Tools addon included with blender."

        # get panel width so we can line wrap print_tools_txt
        tool_shelf = None
        area = bpy.context.area

        for region in area.regions:
            if region.type == 'UI':
                tool_shelf = region

        width = tool_shelf.width / char_width
        wrapped = textwrap.wrap(print_tools_txt, width)

        layout = self.layout

        layout.operator('scene.mt_export_tile', text='Export Tile')
        op = layout.operator('scene.mt_export_object', text='Export Active Object')
        op.voxelise = scene_props.voxelise_on_export
        op.decimate = scene_props.decimate_on_export
        op.make_manifold = scene_props.fix_non_manifold
        op.export_units = scene_props.export_units
        op.filepath = os.path.join(
            prefs.default_export_path,
            obj.name + '.stl')

        layout.prop(prefs, 'default_export_path')
        layout.prop(scene_props, 'export_units')
        layout.prop(scene_props, 'voxelise_on_export')
        layout.prop(scene_props, 'randomise_on_export')
        layout.prop(scene_props, 'decimate_on_export')
        layout.prop(scene_props, 'export_subdivs')

        if scene_props.randomise_on_export is True:
            layout.prop(scene_props, 'num_variants')

        if addon_utils.check("object_print3d_utils") == (True, True):
            layout.prop(scene_props, 'fix_non_manifold')
        else:
            for line in wrapped:
                row = layout.row()
                row.label(text=line)


class MT_OT_Export_Object(bpy.types.Operator, ExportHelper):
    bl_idname = "scene.mt_export_object"
    bl_label = "Export Object"
    bl_description = "Export the active object."
    bl_options = {'REGISTER'}

    filename_ext = ".stl"

    filter_glob: StringProperty(
        default="*.stl",
        options={'HIDDEN'},
        maxlen=255)

    voxelise: BoolProperty(
        name="Voxelise",
        description="Voxelise on Export",
        default=False
    )

    decimate: BoolProperty(
        name="Decimate",
        description="Decimate on Export",
        default=False
    )

    make_manifold: BoolProperty(
        name="Make Manifold",
        description="Make Manifold",
        default=False
    )

    export_units: EnumProperty(
        name="Units",
        description="Default Units",
        items=units
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.mode == 'OBJECT' and obj.type == 'MESH'

    def execute(self, context):
        # set up exporter options
        voxelise_on_export = self.voxelise
        decimate_on_export = self.decimate
        fix_non_manifold = self.make_manifold

        # Controls if we rescale on export
        blend_units = self.export_units
        if blend_units == 'CM':
            unit_multiplier = 10
        elif blend_units == 'INCHES':
            unit_multiplier = 25.4
        else:
            unit_multiplier = 1

        # The object to export
        obj = context.active_object

        if voxelise_on_export or decimate_on_export or fix_non_manifold:
            depsgraph = context.evaluated_depsgraph_get()
            object_eval = obj.evaluated_get(depsgraph)
            mesh_from_eval = bpy.data.meshes.new_from_object(object_eval)
            dup_obj = bpy.data.objects.new('dupe', mesh_from_eval)
            dup_obj.location = obj.location
            dup_obj.rotation_euler = obj.rotation_euler
            dup_obj.scale = obj.scale
            dup_obj.parent = obj.parent
            context.view_layer.active_layer_collection.collection.objects.link(dup_obj)

            if voxelise_on_export:
                voxelise(context, dup_obj)
            if decimate_on_export:
                decimate(context, dup_obj)
            if fix_non_manifold:
                make_manifold(context, dup_obj)

            # export our object
            with bpy.context.temp_override(
                    object=dup_obj,
                    active_object=dup_obj,
                    selected_objects=[dup_obj],
                    selected_editable_objects=[dup_obj]
                    ):
                bpy.ops.export_mesh.stl(
                    filepath=self.filepath,
                    check_existing=True,
                    filter_glob="*.stl",
                    use_selection=True,
                    global_scale=unit_multiplier,
                    use_mesh_modifiers=True)

            bpy.data.objects.remove(dup_obj, do_unlink=True)

        else:
            # export our object
            with bpy.context.temp_override(
                    object=obj,
                    active_object=obj,
                    selected_objects=[obj],
                    selected_editable_objects=[obj]
                    ):
                bpy.ops.export_mesh.stl(
                    filepath=self.filepath,
                    check_existing=True,
                    filter_glob="*.stl",
                    use_selection=True,
                    global_scale=unit_multiplier,
                    use_mesh_modifiers=True)

        self.report({'INFO'}, f'{obj.name} exported to {self.filepath}')

        return {'FINISHED'}

class MT_OT_Export_Tile_Variants(bpy.types.Operator):
    bl_idname = "scene.mt_export_tile"
    bl_label = "Export multiple tile variants"
    bl_options = {'REGISTER'}
    bl_description = "Exports all selected tiles."

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.mode == 'OBJECT' and obj.mt_object_props.is_mt_object is True

    def execute(self, context):
        # set up exporter options
        prefs = get_prefs()
        scene_props = context.scene.mt_scene_props

        # number of variants we will generate
        if scene_props.randomise_on_export:
            num_variants = scene_props.num_variants
        else:
            num_variants = 1

        # set cycles to bake mode and store original settings
        orig_settings = set_cycles_to_bake_mode()

        # voxelise options
        voxelise_on_export = scene_props.voxelise_on_export

        # decimate options
        decimate_on_export = scene_props.decimate_on_export

        # ensure export path exists
        export_path = prefs.default_export_path
        if not os.path.exists(export_path):
            os.mkdir(export_path)

        # Controls if we rescale on export
        blend_units = scene_props.export_units
        if blend_units == 'CM':
            unit_multiplier = 10
        elif blend_units == 'INCHES':
            unit_multiplier = 25.4
        else:
            unit_multiplier = 1

        objects = bpy.data.objects
        visible_objects = []

        # get list of tile collections our selected objects are in. We export
        # all visible objects in the collections
        tile_collections = set()

        for obj in context.selected_objects:
            obj_collections = get_objects_owning_collections(obj.name)

            for collection in obj_collections:
                if collection.mt_tile_props.is_mt_collection is True:
                    tile_collections.add(collection)

        for collection in tile_collections:
            visible_objects = []

            for obj in collection.objects:
                if obj.type == 'MESH' and obj.visible_get() is True and obj.display_type in ['SOLID', 'TEXTURED']:
                    visible_objects.append(obj)

            #generate variants of displacement obs equal to num_variants
            displacement_obs = []
            for obj in visible_objects:
                if obj.mt_object_props.is_displacement:
                    displacement_obs.append((obj, obj.mt_object_props.is_displaced))

            i = 0
            while i < num_variants:
                # construct a random name for our variant
                file_path = os.path.join(
                    export_path,
                    collection.name + '.' + str(random()) + '.stl')

                for ob in displacement_obs:
                    obj = ob[0]
                    obj_props = obj.mt_object_props

                    # check if displacement modifier exists. If it doesn't user has removed it.
                    if obj_props.disp_mod_name in obj.modifiers:

                        if obj_props.is_displacement and obj_props.is_displaced and scene_props.randomise_on_export:
                            set_to_preview(obj)

                        if obj_props.is_displacement and not obj_props.is_displaced:

                            for item in obj.material_slots.items():
                                if item[0]:
                                    material = bpy.data.materials[item[0]]
                                    tree = material.node_tree

                                    # generate a random variant for each displacement object
                                    if scene_props.randomise_on_export:
                                        if num_variants == 1:
                                            if 'Seed' in tree.nodes:
                                                rand = random()
                                                seed_node = tree.nodes['Seed']
                                                seed_node.outputs[0].default_value = rand * 1000
                                        else:
                                            # only generate a random variant on second iteration
                                            if i > 0:
                                                if 'Seed' in tree.nodes:
                                                    rand = random()
                                                    seed_node = tree.nodes['Seed']
                                                    seed_node.outputs[0].default_value = rand * 1000

                            disp_image = bake_displacement_map(obj)
                            disp_strength = obj_props.displacement_strength
                            disp_texture = obj_props.disp_texture

                            disp_texture.image = disp_image
                            disp_mod = obj.modifiers[obj_props.disp_mod_name]
                            disp_mod.texture = disp_texture
                            disp_mod.mid_level = 0
                            disp_mod.strength = disp_strength
                            subsurf_mod = obj.modifiers[obj_props.subsurf_mod_name]
                            subsurf_mod.levels = scene_props.export_subdivs
                            subsurf_mod.show_viewport = True
                            with bpy.context.temp_override(
                                    selected_objects=[obj],
                                    selected_editable_objects=[obj],
                                    active_object=obj,object=obj
                                    ):
                                bpy.ops.object.modifier_move_to_index(
                                    modifier=subsurf_mod.name,
                                    index=0
                                    )
                            obj_props.is_displaced = True

                depsgraph = context.evaluated_depsgraph_get()
                dupes = []

                for obj in visible_objects:
                    object_eval = obj.evaluated_get(depsgraph)
                    mesh_from_eval = bpy.data.meshes.new_from_object(object_eval)
                    dup_obj = bpy.data.objects.new('dupe', mesh_from_eval)
                    dup_obj.data.transform(obj.matrix_world)
                    collection.objects.link(dup_obj)
                    dupes.append(dup_obj)

                context.view_layer.update()
                # join dupes together
                if len(dupes) > 0:

                    bpy.ops.object.select_all(action='DESELECT')
                    for obj in dupes:
                        obj.select_set(True)
                        bpy.context.view_layer.objects.active = dupes[0]
                    #with bpy.context.temp_override(active_object=dupes[0],selected_objects=[dupes[0]]):
                        bpy.ops.object.join()

                    if voxelise_on_export:
                        voxelise(context, dupes[0])
                    if decimate_on_export:
                        decimate(context, dupes[0])
                    if scene_props.fix_non_manifold:
                        make_manifold(context, dupes[0])

                    # set origin to center
                    with bpy.context.temp_override(object=dupes[0],active_object=dupes[0],selected_objects=[dupes[0]],selected_editable_objects=[dupes[0]]):
                        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
                        dupes[0].location = (0, 0, 0)

                    # export our object
                    if (4, 1, 0) < bpy.app.version:
                        #Use the newer, faster bpy.ops.wm.stl_export function 
                        bpy.ops.wm.stl_export(
                            filepath=file_path,
                            check_existing=True,
                            filter_glob="*.stl",
                            export_selected_objects=True,
                            global_scale=unit_multiplier,
                            apply_modifiers=True)
                    else:
                        bpy.ops.export_mesh.stl(
                            filepath=file_path,
                            check_existing=True,
                            filter_glob="*.stl",
                            use_selection=True,
                            global_scale=unit_multiplier,
                            use_mesh_modifiers=True)

                    objects.remove(dupes[0], do_unlink=True)

                    # clean up orphaned meshes
                    for mesh in bpy.data.meshes:
                        if mesh.users == 0:
                            bpy.data.meshes.remove(mesh)
                    i += 1

            # reset displacement obs
            for ob in displacement_obs:
                obj, is_displaced = ob
                if is_displaced is False:
                    set_to_preview(obj)

        reset_renderer_from_bake(orig_settings)

        self.report({'INFO'}, f'{num_variants * len(tile_collections)} tiles exported to {prefs.default_export_path}.')

        return {'FINISHED'}
