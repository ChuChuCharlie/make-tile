import os
from math import radians, cos, sqrt, modf, atan2
import bpy
import bmesh
from mathutils import Vector, Matrix
from bpy.types import Panel, Operator

from bpy.props import (
    EnumProperty,
    FloatProperty,
    StringProperty)

from ..utils.registration import get_prefs

from ..lib.bmturtle.scripts import (
    draw_tri_prism,
    draw_tri_floor_core,
    draw_tri_slot_cutter)
from ..lib.bmturtle.helpers import (
    bmesh_array)

from ..lib.utils.collections import (
    add_object_to_collection)

from ..lib.utils.utils import mode

from .create_tile import (
    convert_to_displacement_core,
    spawn_empty_base,
    set_bool_obj_props,
    set_bool_props,
    MT_Tile_Generator,
    get_subdivs,
    create_material_enums,
    add_subsurf_modifier)

'''
from line_profiler import LineProfiler
from os.path import splitext
profile = LineProfiler()
'''


TRI_LEG_MIN = 0.5
TRI_ANGLE_MIN = 1.0
TRI_ANGLE_MAX = 179.0


def _clamp_prop(self, context, prop_name, min_val, max_val=None):
    """Clamp a FloatProperty to a valid range after UI edits."""
    value = getattr(self, prop_name)
    new_value = value
    if min_val is not None and new_value < min_val:
        new_value = min_val
    if max_val is not None and new_value > max_val:
        new_value = max_val
    if new_value != value:
        setattr(self, prop_name, new_value)


def _clamp_triangular_props(op):
    """Clamp triangular tile dimensions before generation."""
    op.leg_1_len = max(TRI_LEG_MIN, op.leg_1_len)
    op.leg_2_len = max(TRI_LEG_MIN, op.leg_2_len)
    op.angle = min(TRI_ANGLE_MAX, max(TRI_ANGLE_MIN, op.angle))


class MT_PT_Triangular_Floor_Panel(Panel):
    """Draw a tile options panel in UI."""

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Make Tile"
    bl_label = "Tile Options"
    bl_order = 2
    bl_idname = "MT_PT_Triangular_Floor_Panel"
    bl_description = "Options to configure the dimensions of a tile"

    @classmethod
    def poll(cls, context):
        """Check tile_type."""
        if hasattr(context.scene, 'mt_scene_props'):
            return context.scene.mt_scene_props.tile_type in ["TRIANGULAR_FLOOR"]
        return False

    def draw(self, context):
        """Draw the Panel."""
        scene = context.scene
        scene_props = scene.mt_scene_props
        layout = self.layout

        layout.label(text="Blueprints")
        layout.prop(scene_props, 'base_blueprint')
        layout.prop(scene_props, 'main_part_blueprint', text="Main")

        if scene_props.base_blueprint not in ('PLAIN', 'NONE'):
            layout.prop(scene_props, 'base_socket_type')

        layout.label(text="Material")
        layout.prop(scene_props, 'floor_material')

        layout.label(text="Tile Properties")
        layout.prop(scene_props, 'tile_z', text='Tile Height')
        layout.prop(scene_props, 'leg_1_len', text='Leg 1 Length')
        layout.prop(scene_props, 'leg_2_len', text='Leg 2 Length')
        layout.prop(scene_props, 'angle', text='Angle')

        layout.label(text="Sync Proportions")
        layout.prop(scene_props, 'z_proportionate_scale')

        layout.label(text="Base Properties")
        layout.prop(scene_props, 'base_z', text='Base Height')

        layout.label(text="Subdivision Density")
        layout.prop(scene_props, 'subdivision_density', text="")

        layout.label(text="UV Island Margin")
        layout.prop(scene_props, 'UV_island_margin', text="")

        layout.operator('scene.reset_tile_defaults')


class MT_OT_Make_Triangular_Floor_Tile(Operator, MT_Tile_Generator):
    """Operator. Create a Triangular Floor Tile."""

    bl_idname = "object.make_triangular_floor"
    bl_label = "Triangle Floor"
    bl_options = {'UNDO', 'REGISTER'}
    mt_blueprint = "CUSTOM"
    mt_type = "TRIANGULAR_FLOOR"

    angle: FloatProperty(
        name="Base Angle",
        description="Angle between leg 1 and leg 2",
        default=90,
        min=TRI_ANGLE_MIN,
        max=TRI_ANGLE_MAX,
        soft_min=TRI_ANGLE_MIN,
        soft_max=TRI_ANGLE_MAX,
        step=500,
        precision=0,
        update=lambda self, context: _clamp_prop(
            self, context, 'angle', TRI_ANGLE_MIN, TRI_ANGLE_MAX)
    )

    leg_1_len: FloatProperty(
        name="Leg 1 Length",
        description="Length of leg",
        default=2,
        min=TRI_LEG_MIN,
        soft_min=TRI_LEG_MIN,
        step=50,
        precision=1,
        update=lambda self, context: _clamp_prop(
            self, context, 'leg_1_len', TRI_LEG_MIN)
    )

    leg_2_len: FloatProperty(
        name="Leg 2 Length",
        description="Length of leg",
        default=2,
        min=TRI_LEG_MIN,
        soft_min=TRI_LEG_MIN,
        step=50,
        precision=1,
        update=lambda self, context: _clamp_prop(
            self, context, 'leg_2_len', TRI_LEG_MIN)
    )

    floor_material: EnumProperty(
        items=create_material_enums,
        name="Floor Material")

    # @profile
    def exec(self, context):
        base_blueprint = self.base_blueprint
        core_blueprint = self.main_part_blueprint
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props

        if base_blueprint == 'NONE':
            base = spawn_empty_base(tile_props)
        elif base_blueprint == 'OPENLOCK':
            base = spawn_openlock_base(self, tile_props)
        elif base_blueprint == 'PLAIN':
            base = spawn_plain_base(tile_props)

        if core_blueprint == 'NONE':
            core = None
        else:
            core = create_plain_triangular_floor_cores(base, tile_props)
        self.finalise_tile(context, base, core)

    def execute(self, context):
        """Execute the operator."""
        _clamp_triangular_props(self)
        super().execute(context)
        if not self.refresh:
            return {'PASS_THROUGH'}
        self.exec(context)
        # profile.dump_stats(splitext(__file__)[0] + '.prof')

        return {'FINISHED'}

    def init(self, context):
        super().init(context)
        tile_collection = bpy.data.collections[self.tile_name]
        tile_props = tile_collection.mt_tile_props
        tile_props.collection_type = "TILE"
        tile_props.tile_size = (self.tile_x, self.tile_y, self.tile_z)
        tile_props.base_size = (self.base_x, self.base_y, self.base_z)

    def draw(self, context):
        super().draw(context)
        layout = self.layout
        layout.label(text="Blueprints")
        layout.prop(self, 'base_blueprint')
        layout.prop(self, 'main_part_blueprint', text="Main")

        if self.base_blueprint not in ('PLAIN', 'NONE'):
            layout.prop(self, 'base_socket_type')

        layout.label(text="Material")
        layout.prop(self, 'floor_material')

        layout.label(text="Tile Properties")
        layout.prop(self, 'tile_z', text='Tile Height')
        layout.prop(self, 'leg_1_len', text='Leg 1 Length')
        layout.prop(self, 'leg_2_len', text='Leg 2 Length')
        layout.prop(self, 'angle', text='Angle')

        layout.label(text="Sync Proportions")
        layout.prop(self, 'z_proportionate_scale')

        layout.label(text="Base Properties")
        layout.prop(self, 'base_z', text='Base Height')

        layout.label(text="UV Island Margin")
        layout.prop(self, 'UV_island_margin', text="")


class MT_OT_Make_Openlock_Triangular_Base(MT_Tile_Generator, Operator):
    """Internal Operator. Generate an OpenLOCK triangular base."""

    bl_idname = "object.make_openlock_triangular_base"
    bl_label = "Triangular Base"
    bl_options = {'INTERNAL'}
    mt_blueprint = "OPENLOCK"
    mt_type = "TRIANGULAR_BASE"

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        spawn_openlock_base(tile_props)
        return{'FINISHED'}


class MT_OT_Make_Plain_Triangular_Base(MT_Tile_Generator, Operator):
    """Internal Operator. Generate a plain triangular base."""

    bl_idname = "object.make_plain_triangular_base"
    bl_label = "Triangular Base"
    bl_options = {'INTERNAL'}
    mt_blueprint = "PLAIN"
    mt_type = "TRIANGULAR_BASE"

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        spawn_plain_base(tile_props)
        return{'FINISHED'}


class MT_OT_Make_Empty_Triangular_Base(MT_Tile_Generator, Operator):
    """Internal Operator. Generate an empty triangular base."""

    bl_idname = "object.make_empty_triangular_base"
    bl_label = "Triangular Base"
    bl_options = {'INTERNAL'}
    mt_blueprint = "NONE"
    mt_type = "TRIANGULAR_BASE"

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        spawn_empty_base(tile_props)
        return{'FINISHED'}


class MT_OT_Make_Plain_Triangular_Floor_Core(MT_Tile_Generator, Operator):
    """Internal Operator. Generate a plain triangular core."""

    bl_idname = "object.make_plain_triangular_floor_core"
    bl_label = "Triangular Floor Core"
    bl_options = {'INTERNAL'}
    mt_blueprint = "PLAIN"
    mt_type = "TRIANGULAR_FLOOR_CORE"
    base_name: StringProperty()

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        base = bpy.data.objects[self.base_name]
        create_plain_triangular_floor_cores(base, tile_props)
        return{'FINISHED'}


class MT_OT_Make_Openlock_Triangular_Floor_Core(MT_Tile_Generator, Operator):
    """Internal Operator. Generate an openlock triangular floor core."""

    bl_idname = "object.make_openlock_triangular_floor_core"
    bl_label = "Triangular Floor Core"
    bl_options = {'INTERNAL'}
    mt_blueprint = "OPENLOCK"
    mt_type = "TRIANGULAR_FLOOR_CORE"
    base_name: StringProperty()

    def execute(self, context):
        """Execute the operator."""
        tile_props = bpy.data.collections[self.tile_name].mt_tile_props
        base = bpy.data.objects[self.base_name]
        create_plain_triangular_floor_cores(base, tile_props)
        return{'FINISHED'}


class MT_OT_Make_Empty_Triangular_Floor_Core(MT_Tile_Generator, Operator):
    """Internal Operator. Generate an empty triangular floor core."""

    bl_idname = "object.make_empty_triangular_floor_core"
    bl_label = "Triangular Floor Core"
    bl_options = {'INTERNAL'}
    mt_blueprint = "NONE"
    mt_type = "TRIANGULAR_FLOOR_CORE"
    base_name: StringProperty()

    def execute(self, context):
        """Execute the operator."""
        return {'PASS_THROUGH'}


def spawn_plain_base(tile_props):
    """Spawn a plain base into the scene.

    Args:
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: tile base
    """
    tile_name = tile_props.tile_name
    base = draw_tri_prism(dimensions={
        'b': tile_props.leg_1_len,
        'c': tile_props.leg_2_len,
        'A': tile_props.angle,
        'height': tile_props.base_size[2]
    })

    base.name = tile_name + '.base'
    add_object_to_collection(base, tile_name)

    obj_props = base.mt_object_props
    obj_props.is_mt_object = True
    obj_props.geometry_type = 'BASE'
    obj_props.tile_name = tile_name
    bpy.context.view_layer.objects.active = base

    return base


def spawn_openlock_base(self, tile_props):
    """Spawn an OpenLOCK base into the scene.

    Args:
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: tile base
    """
    dimensions = {
        'b': tile_props.leg_1_len,
        'c': tile_props.leg_2_len,
        'A': tile_props.angle,
        'height': tile_props.base_size[2]}
    tile_name = tile_props.tile_name

    base, dimensions = draw_tri_prism(dimensions, True)

    base.name = tile_name + '.base'
    add_object_to_collection(base, tile_name)

    clip_cutters = spawn_openlock_base_clip_cutters(
        self, dimensions, tile_props)

    for clip_cutter in clip_cutters:
        set_bool_obj_props(clip_cutter, base, tile_props, 'DIFFERENCE')
        set_bool_props(clip_cutter, base, 'DIFFERENCE')

    # The slot cutter is only viable when both legs are at least 1.5.
    # On smaller triangles it clips through adjacent geometry.
    if dimensions['b'] >= 1.5 and dimensions['c'] >= 1.5:
        slot_cutter = draw_tri_slot_cutter(dimensions)
        set_bool_obj_props(slot_cutter, base, tile_props, 'DIFFERENCE')
        set_bool_props(slot_cutter, base, 'DIFFERENCE')

    obj_props = base.mt_object_props
    obj_props.is_mt_object = True
    obj_props.geometry_type = 'BASE'
    obj_props.tile_name = tile_name
    bpy.context.view_layer.objects.active = base
    return base


# @profile
def spawn_openlock_base_clip_cutters(self, dimensions, tile_props):
    """Make cutters for the openlock base clips.

    Args:
        dimensions (dict): calculated triangle dimensions
        tile_props (mt_tile_props): tile properties

    Returns:
        list[bpy.types.Object]: base clip cutters

    """
    #      B
    #      /\
    #   c /  \ a
    #    /    \
    #   /______\
    #  A    b    C

    # b = Leg 1
    # c = Leg 2

    a = dimensions['a']
    b = dimensions['b']
    c = dimensions['c']
    A = dimensions['A']
    B = dimensions['B']
    C = dimensions['C']

    cutters = []

    # Clip cutters and the slot cutter are only used when at least one leg is
    # longer than 1.5. If both legs are <= 1.5 there is not enough room and the
    # booleans clip through adjacent geometry.
    if b <= 1.5 and c <= 1.5:
        return cutters

    # Only load cutter assets when at least one leg is long enough for a clip
    # cutter or an isosceles right triangle hypotenuse cutter is needed.
    if b >= 2 or c >= 2 or (A == 90 and b == c and a > 1.5):
        preferences = get_prefs()
        cutter_file = self.get_base_socket_filename()
        booleans_path = os.path.join(
            preferences.assets_path,
            "meshes",
            "booleans",
            cutter_file)

        with bpy.data.libraries.load(booleans_path) as (data_from, data_to):
            if self.base_socket_type == 'OPENLOCK':
                data_to.objects = [
                    'openlock.wall.base.cutter.clip.001',
                    'openlock.wall.base.cutter.clip.cap.start.001',
                    'openlock.wall.base.cutter.clip.cap.end.001']
            elif self.base_socket_type == 'OPENLOCK-NoSupport':
                data_to.objects = [
                    'openlock.wall.base.cutter.clip.001.nosupp',
                    'openlock.wall.base.cutter.clip.cap.start.001',
                    'openlock.wall.base.cutter.clip.cap.end.001']

        cutter = data_to.objects[0]
        cutter_start_cap = data_to.objects[1]
        cutter_end_cap = data_to.objects[2]

        if b >= 2:
            # If the adjacent leg is short (<= 1.5), cap this leg at
            # floor(leg) - 1 total cutters so the strip does not reach the
            # short-leg corner / hypotenuse. Otherwise use the normal
            # angle-based length.
            reduce_mode = c <= 1.5
            leg_1_cutter = _spawn_leg_1_cutter(
                dimensions,
                cutter,
                cutter_start_cap,
                cutter_end_cap,
                tile_props,
                reduce_mode)
            if leg_1_cutter is not None:
                cutters.append(leg_1_cutter)

        if c >= 2:
            reduce_mode = b <= 1.5
            leg_2_cutter = _spawn_leg_2_cutter(
                dimensions,
                cutter,
                cutter_start_cap,
                cutter_end_cap,
                tile_props,
                reduce_mode)
            if leg_2_cutter is not None:
                cutters.append(leg_2_cutter)

        if A == 90 and b == c and a > 1.5:
            cutters.append(_spawn_hypotenuse_cutter(
                dimensions,
                cutter,
                cutter_start_cap,
                cutter_end_cap,
                tile_props))

        bpy.data.objects.remove(cutter)
        bpy.data.objects.remove(cutter_start_cap)
        bpy.data.objects.remove(cutter_end_cap)

    return cutters


def _spawn_leg_1_cutter(
        dimensions,
        cutter,
        cutter_start_cap,
        cutter_end_cap,
        tile_props,
        reduce_mode=False):
    """Create the OpenLOCK clip cutter for Leg 1 (side b).

    Returns None when reduce mode would produce zero cutters, so the caller
    can skip adding a boolean modifier for that leg.
    """
    b = dimensions['b']
    A = dimensions['A']
    C = dimensions['C']
    loc_A = dimensions['loc_A']

    me = cutter.data.copy()
    b_cutter = bpy.data.objects.new("Leg 1 Cutter", me)
    bm = bmesh.new()
    bm.from_mesh(me)
    add_object_to_collection(b_cutter, tile_props.tile_name)

    # Use the standard angle-based fit length unless the adjacent leg is too
    # short to leave room for the full strip. In reduce mode the total number
    # of cutters scales indefinitely with leg length using floor(leg) - 1
    # cutters (1 for 2.x, 2 for 3.x, 3 for 4.x, 4 for 5.x, ...). The source
    # cutter object already counts as one cutter, so the target number of
    # duplicates is desired_total - 1.
    if reduce_mode:
        cutter_offset = b_cutter.dimensions.x
        desired_total = max(0, int(b) - 1)
        if desired_total == 0:
            bpy.data.objects.remove(b_cutter)
            bm.free()
            return None
        duplicate_count = desired_total - 1
        fit_length = (duplicate_count + 0.5) * cutter_offset
    elif A >= 90:
        if C >= 90:
            fit_length = b - 1
        else:
            fit_length = b - 1.5
    elif A < 90:
        if C >= 90:
            fit_length = b - 1.5
        else:
            fit_length = b - 2

    bm = bmesh_array(
        source_obj=b_cutter,
        source_bm=bm,
        start_cap=cutter_start_cap,
        end_cap=cutter_end_cap,
        relative_offset_displace=(1, 0, 0),
        fit_type='FIT_LENGTH',
        fit_length=fit_length)

    bmesh.ops.translate(
        bm,
        verts=bm.verts,
        vec=(0.5, 0.25, 0),
        space=b_cutter.matrix_world)

    bmesh.ops.rotate(
        bm,
        cent=loc_A,
        verts=bm.verts,
        matrix=Matrix.Rotation(radians(A - 90) * -1, 3, 'Z'),
        space=b_cutter.matrix_world)

    bm.to_mesh(me)
    bm.free()
    return b_cutter


def _spawn_leg_2_cutter(
        dimensions,
        cutter,
        cutter_start_cap,
        cutter_end_cap,
        tile_props,
        reduce_mode=False):
    """Create the OpenLOCK clip cutter for Leg 2 (side c).

    Returns None when reduce mode would produce zero cutters, so the caller
    can skip adding a boolean modifier for that leg.
    """
    c = dimensions['c']
    A = dimensions['A']
    B = dimensions['B']
    loc_A = dimensions['loc_A']

    me = cutter.data.copy()
    c_cutter = bpy.data.objects.new("Leg 2 Cutter", me)
    bm = bmesh.new()
    bm.from_mesh(me)
    add_object_to_collection(c_cutter, tile_props.tile_name)

    # Use the standard angle-based fit length unless the adjacent leg is too
    # short to leave room for the full strip. In reduce mode the total number
    # of cutters scales indefinitely with leg length using floor(leg) - 1
    # cutters (1 for 2.x, 2 for 3.x, 3 for 4.x, 4 for 5.x, ...). The source
    # cutter object already counts as one cutter, so the target number of
    # duplicates is desired_total - 1.
    translate_y = c - 1
    if reduce_mode:
        cutter_offset = c_cutter.dimensions.x
        desired_total = max(0, int(c) - 1)
        if desired_total == 0:
            bpy.data.objects.remove(c_cutter)
            bm.free()
            return None
        duplicate_count = desired_total - 1
        fit_length = (duplicate_count + 0.5) * cutter_offset
        # Anchor the strip near corner A instead of corner B by translating
        # only by the arrayed length plus a small margin. This keeps the
        # cutter from shifting past the short-leg corner / hypotenuse.
        translate_y = 0.5 + duplicate_count * cutter_offset
    elif B >= 90:
        if A >= 90:
            fit_length = c - 1
        else:
            fit_length = c - 1.5
    elif B < 90:
        if A >= 90:
            fit_length = c - 1.5
        else:
            fit_length = c - 2

    bm = bmesh_array(
        source_obj=c_cutter,
        source_bm=bm,
        start_cap=cutter_start_cap,
        end_cap=cutter_end_cap,
        relative_offset_displace=(1, 0, 0),
        fit_type='FIT_LENGTH',
        fit_length=fit_length)

    bmesh.ops.rotate(
        bm,
        cent=loc_A,
        verts=bm.verts,
        matrix=Matrix.Rotation(radians(-90), 3, 'Z'),
        space=c_cutter.matrix_world)
    bmesh.ops.translate(
        bm,
        verts=bm.verts,
        vec=(0.25, translate_y, 0.0001),
        space=c_cutter.matrix_world)

    bm.to_mesh(me)
    bm.free()
    return c_cutter


def _spawn_hypotenuse_cutter(
        dimensions,
        cutter,
        cutter_start_cap,
        cutter_end_cap,
        tile_props):
    """Create the OpenLOCK clip cutter for the hypotenuse (side a).

    Only used for isosceles right triangles.
    """
    a = dimensions['a']
    A = dimensions['A']
    b = dimensions['b']
    loc_A = dimensions['loc_A']
    loc_B = dimensions['loc_B']
    loc_C = dimensions['loc_C']

    me = cutter.data.copy()
    a_cutter = bpy.data.objects.new("Leg 3 Cutter", me)
    bm = bmesh.new()
    bm.from_mesh(me)
    add_object_to_collection(a_cutter, tile_props.tile_name)

    # Array the clip cutters from the centre of the hypotenuse toward
    # corners B and C, leaving a margin for the end caps.
    cutter_offset = cutter.dimensions.x
    fit_length = max(0, a - 1.5)
    array_count = modf(fit_length / cutter_offset)[1]
    half_span = (array_count * cutter_offset) / 2

    bm = bmesh_array(
        source_obj=a_cutter,
        source_bm=bm,
        start_cap=cutter_start_cap,
        end_cap=cutter_end_cap,
        relative_offset_displace=(1, 0, 0),
        fit_length=fit_length,
        fit_type='FIT_LENGTH')

    # Centre the array along its local X axis.
    bmesh.ops.translate(
        bm,
        verts=bm.verts,
        vec=(-half_span, 0, 0),
        space=a_cutter.matrix_world)

    # Align the strip with the hypotenuse and place it at the midpoint,
    # offset inward by half the base thickness.
    midpoint = (loc_B + loc_C) / 2
    inward = (loc_A - midpoint).normalized()
    target = midpoint + inward * 0.25

    hyp_dir = loc_C - loc_B
    angle = atan2(hyp_dir.y, hyp_dir.x)

    bmesh.ops.rotate(
        bm,
        verts=bm.verts,
        cent=(0, 0, 0),
        matrix=Matrix.Rotation(angle + radians(180), 3, 'Z'),
        space=a_cutter.matrix_world)

    bmesh.ops.translate(
        bm,
        verts=bm.verts,
        vec=(target.x, target.y, 0.0002),
        space=a_cutter.matrix_world)

    bm.to_mesh(me)
    bm.free()
    return a_cutter


def create_plain_triangular_floor_cores(base, tile_props):
    """Create preview and displacement cores.

    Args:
        base (bpy.types.Object): tile base
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: preview core
    """
    core = spawn_floor_core(tile_props)
    textured_vertex_groups = ['Top']
    material = tile_props.floor_material
    subsurf = add_subsurf_modifier(core)
    convert_to_displacement_core(
        core,
        textured_vertex_groups,
        material,
        subsurf)

    return core


def spawn_floor_core(tile_props):
    """Spawn the core (top part) of a floor tile.

    Args:
        tile_props (MakeTile.properties.MT_Tile_Properties): tile properties

    Returns:
        bpy.types.Object: tile core
    """
    tile_name = tile_props.tile_name
    b = tile_props.leg_1_len
    c = tile_props.leg_2_len
    A = tile_props.angle
    hyp = sqrt((b**2 + c**2) - ((2 * b * c) * cos(radians(A))))
    native_subdivisions = get_subdivs(
        tile_props.subdivision_density,
        [hyp, tile_props.tile_size[2] - tile_props.base_size[2]])
    core = draw_tri_floor_core(
        dimensions={
            'b': b,
            'c': c,
            'A': A,
            'height': tile_props.tile_size[2] - tile_props.base_size[2]
        },
        subdivs=native_subdivisions
    )
    core.name = tile_name + '.core'
    add_object_to_collection(core, tile_name)

    mode('OBJECT')

    core.location[2] = core.location[2] + tile_props.base_size[2]

    obj_props = core.mt_object_props
    obj_props.is_mt_object = True
    obj_props.tile_name = tile_props.tile_name
    bpy.context.view_layer.objects.active = core

    return core
