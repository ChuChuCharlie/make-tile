import bpy
from .. lib.utils.selection import select, deselect_all, select_all, activate
from .. lib.utils.utils import mode, add_deform_modifiers
from mathutils import Vector
from .. lib.turtle.scripts.primitives import draw_cuboid, draw_tri_prism
from math import radians


class MT_OT_Tile_Trimmer(bpy.types.Operator):
    """Operator class used to trim tiles before export"""
    bl_idname = "scene.trim_tile"
    bl_label = "Trim Tile"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        if obj is not None:
            return bpy.context.object.mode == 'OBJECT'

    def execute(self, context):
        # object to be trimmed
        obj = context.active_object

        # get collection name / name of tile
        tile_name = obj.users_collection[0].name

        # get tile empty with properties stored on it
        if tile_name + '.empty' in bpy.data.objects:
            tile_empty = bpy.data.objects[tile_name + '.empty']
            trimmers = tile_empty['tile_properties']['trimmers']

            if context.scene.mt_trim_x_neg is True:
                trimmer = trimmers['x_neg']
                trim_side(obj, trimmer, context.scene.mt_trim_buffer)
            if context.scene.mt_trim_x_pos is True:
                trimmer = trimmers['x_pos']
                trim_side(obj, trimmer, context.scene.mt_trim_buffer)
            if context.scene.mt_trim_y_neg is True:
                trimmer = trimmers['y_neg']
                trim_side(obj, trimmer, context.scene.mt_trim_buffer)
            if context.scene.mt_trim_y_pos is True:
                trimmer = trimmers['y_pos']
                trim_side(obj, trimmer, context.scene.mt_trim_buffer)
            if context.scene.mt_trim_z_neg is True:
                trimmer = trimmers['z_neg']
                trim_side(obj, trimmer, context.scene.mt_trim_buffer)
            if context.scene.mt_trim_z_pos is True:
                trimmer = trimmers['z_pos']
                trim_side(obj, trimmer, context.scene.mt_trim_buffer)

        return {'FINISHED'}

    @classmethod
    def register(cls):
        bpy.types.Scene.mt_trim_buffer = bpy.props.FloatProperty(
            name="Buffer",
            description="Buffer to use for trimming. Helps Booleans work",
            default=-0.001,
            precision=4
        )

        bpy.types.Scene.mt_trim_x_neg = bpy.props.BoolProperty(
            name="X Negative",
            description="Trim the X negative side of tile",
            default=False
        )

        bpy.types.Scene.mt_trim_x_pos = bpy.props.BoolProperty(
            name="X Positive",
            description="Trim the X positive side of tile",
            default=False
        )

        bpy.types.Scene.mt_trim_y_neg = bpy.props.BoolProperty(
            name="Y Negative",
            description="Trim the Y negative side of tile",
            default=False
        )

        bpy.types.Scene.mt_trim_y_pos = bpy.props.BoolProperty(
            name="Y Positive",
            description="Trim the Y positive side of tile",
            default=False
        )

        bpy.types.Scene.mt_trim_z_neg = bpy.props.BoolProperty(
            name="Z Negative",
            description="Trim the Z positive side of tile",
            default=False
        )

        bpy.types.Scene.mt_trim_z_pos = bpy.props.BoolProperty(
            name="Z Positive",
            description="Trim the Z positive side of tile",
            default=False
        )

    @classmethod
    def unregister(cls):
        del bpy.types.Scene.mt_trim_buffer
        del bpy.types.Scene.mt_trim_x_neg
        del bpy.types.Scene.mt_trim_x_pos
        del bpy.types.Scene.mt_trim_y_neg
        del bpy.types.Scene.mt_trim_y_pos
        del bpy.types.Scene.mt_trim_z_neg
        del bpy.types.Scene.mt_trim_z_pos


def create_corner_wall_tile_trimmers(tile_properties):
    deselect_all()

    cursor = bpy.context.scene.cursor
    cursor_orig_location = cursor.location.copy()

    bbox_proxy = draw_cuboid([
        tile_properties['x_leg'],
        tile_properties['y_leg'],
        tile_properties['tile_size'][2]])

    mode('OBJECT')

    # get bounding box and dimensions of cuboid
    bound_box = bbox_proxy.bound_box
    dimensions = bbox_proxy.dimensions.copy()

    # create trimmers
    buffer = bpy.context.scene.mt_trim_buffer
    x_neg_trimmer = create_x_neg_trimmer(bound_box, dimensions, buffer)
    x_neg_trimmer.name = tile_properties['tile_name'] + '.x_neg_trimmer'
    x_pos_trimmer = create_x_pos_trimmer(bound_box, dimensions, buffer)
    x_pos_trimmer.name = tile_properties['tile_name'] + '.x_pos_trimmer'
    y_neg_trimmer = create_y_neg_trimmer(bound_box, dimensions, buffer)
    y_neg_trimmer.name = tile_properties['tile_name'] + '.y_neg_trimmer'
    y_pos_trimmer = create_y_pos_trimmer(bound_box, dimensions, buffer)
    y_pos_trimmer.name = tile_properties['tile_name'] + '.y_pos_trimmer'
    z_pos_trimmer = create_z_pos_trimmer(bound_box, dimensions, buffer)
    z_pos_trimmer.name = tile_properties['tile_name'] + '.z_pos_trimmer'
    z_neg_trimmer = create_z_neg_trimmer(bound_box, dimensions, buffer)
    z_neg_trimmer.name = tile_properties['tile_name'] + '.z_neg_trimmer'

    trimmers = {
        'x_neg': x_neg_trimmer,
        'x_pos': x_pos_trimmer,
        'y_neg': y_neg_trimmer,
        'y_pos': y_pos_trimmer,
        'z_pos': z_pos_trimmer,
        'z_neg': z_neg_trimmer
    }

    cursor.location = cursor_orig_location

    for trimmer in trimmers.values():
        trimmer.display_type = 'BOUNDS'
        select(trimmer.name)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        trimmer.hide_viewport = True
        trimmer.parent = bpy.context.scene.objects[tile_properties['empty_name']]

    bpy.ops.object.delete({"selected_objects": [bbox_proxy]})
    return trimmers


def create_curved_wall_tile_trimmers(tile_properties):
    deselect_all()

    cursor = bpy.context.scene.cursor
    cursor_orig_location = cursor.location.copy()
    tile_size = tile_properties['tile_size']
    # create a cuboid the size of our tile and center it to use
    # as our bounding box for entire tile for Z trimmers
    if tile_properties['base_blueprint'] is not 'NONE':
        bbox_proxy = draw_cuboid(Vector((
            tile_size[0],
            tile_properties['base_size'][1],
            tile_size[2])))
    else:
        bbox_proxy = draw_cuboid(tile_size)
    mode('OBJECT')

    bbox_proxy.location = (
        bbox_proxy.location[0] - bbox_proxy.dimensions[0] / 2,
        bbox_proxy.location[1] - bbox_proxy.dimensions[1] / 2,
        bbox_proxy.location[2])

    cursor.location = cursor_orig_location
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

    # get bounding box and dimensions of cuboid
    bound_box = bbox_proxy.bound_box
    dimensions = bbox_proxy.dimensions.copy()

    buffer = bpy.context.scene.mt_trim_buffer

    # create x trimmers
    x_pos_trimmer = draw_cuboid(Vector((1, tile_size[1] + 1, tile_size[2] + 1)))
    x_pos_trimmer.name = tile_properties['tile_name'] + '.x_pos_trimmer'
    mode('OBJECT')
    x_pos_trimmer.location = (
        x_pos_trimmer.location[0],
        x_pos_trimmer.location[1] - x_pos_trimmer.dimensions[1] / 2,
        x_pos_trimmer.location[2] - 0.5)
    cursor.location = cursor_orig_location
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

    circle_center = Vector((
        x_pos_trimmer.location[0],
        x_pos_trimmer.location[1] + tile_properties['wall_inner_radius'],
        x_pos_trimmer.location[2]))

    bpy.ops.transform.rotate(
        value=-radians((tile_properties['degrees_of_arc'] / 2)),
        orient_axis='Z',
        orient_type='GLOBAL',
        center_override=circle_center)

    x_neg_trimmer = draw_cuboid(Vector((-1, tile_size[1] + 1, tile_size[2] + 1)))
    x_neg_trimmer.name = tile_properties['tile_name'] + 'x_neg_trimmer'
    mode('OBJECT')
    x_neg_trimmer.location = (
        x_neg_trimmer.location[0],
        x_neg_trimmer.location[1] - x_neg_trimmer.dimensions[1] / 2,
        x_neg_trimmer.location[2] - 0.5)
    cursor.location = cursor_orig_location
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

    bpy.ops.transform.rotate(
        value=radians(tile_properties['degrees_of_arc'] / 2),
        orient_axis='Z',
        orient_type='GLOBAL',
        center_override=circle_center)

    mode('OBJECT')

    cursor.location = cursor_orig_location
    # create Z trimmers
    z_pos_trimmer = create_z_pos_trimmer(bound_box, dimensions, buffer)
    z_pos_trimmer.name = tile_properties['tile_name'] + '.z_pos_trimmer'

    z_neg_trimmer = create_z_neg_trimmer(bound_box, dimensions, buffer)
    z_neg_trimmer.name = tile_properties['tile_name'] + '.z_neg_trimmer'

    cursor.location = cursor_orig_location
    z_trimmers = [z_pos_trimmer, z_neg_trimmer]

    for trimmer in z_trimmers:
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        add_deform_modifiers(trimmer, tile_properties['segments'], tile_properties['degrees_of_arc'])

    trimmers = {
        'x_neg': x_neg_trimmer,
        'x_pos': x_pos_trimmer,
        'z_pos': z_pos_trimmer,
        'z_neg': z_neg_trimmer
    }

    cursor.location = cursor_orig_location

    for trimmer in trimmers.values():
        trimmer.display_type = 'BOUNDS'
        select(trimmer.name)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        trimmer.hide_viewport = True
        trimmer.parent = bpy.context.scene.objects[tile_properties['empty_name']]

    bpy.ops.object.delete({"selected_objects": [bbox_proxy]})
    return trimmers


def create_tri_floor_tile_trimmers(tile_properties, dim):
    mode('OBJECT')
    deselect_all()

    cursor = bpy.context.scene.cursor
    cursor_orig_location = cursor.location.copy()

    b_trimmer = create_b_trimmer(dim)
    b_trimmer.name = tile_properties['tile_name'] + '.b_trimmer'
    c_trimmer = create_c_trimmer(dim)
    c_trimmer.name = tile_properties['tile_name'] + '.c_trimmer'
    a_trimmer = create_a_trimmer(dim)
    a_trimmer.name = tile_properties['tile_name'] + '.a_trimmer'
    z_pos_trimmer = create_z_pos_tri_trimmer(dim, tile_properties)
    z_pos_trimmer.name = tile_properties['tile_name'] + '.z_pos_trimmer'
    z_neg_trimmer = create_z_neg_tri_trimmer(dim, tile_properties)
    z_neg_trimmer.name = tile_properties['tile_name'] + '.z_neg_trimmer'

    trimmers = {
        'x_neg': b_trimmer,
        'y_neg': c_trimmer,
        'x_pos': a_trimmer,
        'z_pos': z_pos_trimmer,
        'z_neg': z_neg_trimmer
    }

    for trimmer in trimmers.values():
        trimmer.display_type = 'BOUNDS'
        select(trimmer.name)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        trimmer.hide_viewport = True
        trimmer.parent = bpy.context.scene.objects[tile_properties['empty_name']]

    return trimmers


def create_z_neg_tri_trimmer(dim, tile_properties):
    turtle = bpy.context.scene.cursor
    t = bpy.ops.turtle
    buffer = bpy.context.scene.mt_trim_buffer
    turtle.location = (
        dim['loc_A'][0] - 0.25,
        dim['loc_A'][1] - 0.25,
        dim['loc_A'][2] + buffer
    )
    t.add_turtle()
    t.pu()

    trimmer = bpy.context.object
    t.add_vert()
    t.pd()
    trimmer, dimensions = draw_tri_prism(dim['b'] + 1, dim['c'] + 1, dim['A'], -1)
    t.select_all()
    t.pu()
    t.home()
    mode('OBJECT')

    return trimmer


def create_z_pos_tri_trimmer(dim, tile_properties):
    turtle = bpy.context.scene.cursor
    t = bpy.ops.turtle
    buffer = bpy.context.scene.mt_trim_buffer
    turtle.location = (
        dim['loc_A'][0] - 0.25,
        dim['loc_A'][1] - 0.25,
        dim['loc_A'][2] + tile_properties['tile_size'][2]
    )
    t.add_turtle()
    t.pu()

    trimmer = bpy.context.object
    t.add_vert()
    t.pd()
    trimmer, dimensions = draw_tri_prism(dim['b'] + 1, dim['c'] + 1, dim['A'], 1)
    t.select_all()
    t.pu()
    t.home()
    mode('OBJECT')

    return trimmer


def create_a_trimmer(dim):
    turtle = bpy.context.scene.cursor
    t = bpy.ops.turtle
    buffer = bpy.context.scene.mt_trim_buffer

    t.add_turtle()
    t.pu()

    trimmer = bpy.context.object

    # TODO: fix difference between loc_B and angle B
    t.setp(v=dim['loc_B'])
    t.rt(d=180 - dim['C'])
    t.ri(d=buffer)
    t.bk(d=0.5)
    t.dn(d=0.5)
    t.pd()
    t.add_vert()
    t.up(d=dim['height'] + 1)
    t.select_all()
    t.lf(d=1)
    t.select_all()
    t.fd(d=1 + dim['a'])
    t.pu()
    t.home()
    mode('OBJECT')

    return trimmer


def create_c_trimmer(dim):
    turtle = bpy.context.scene.cursor
    t = bpy.ops.turtle
    buffer = bpy.context.scene.mt_trim_buffer

    t.add_turtle()
    t.pu()

    trimmer = bpy.context.object

    t.setp(v=dim['loc_A'])
    t.rt(d=dim['A'])
    t.bk(d=0.5)
    t.lf(d=buffer)
    t.dn(d=0.5)
    t.pd()
    t.add_vert()
    t.up(d=dim['height'] + 1)
    t.select_all()
    t.fd(d=dim['c'] + 1)
    t.select_all()
    t.ri(d=1)
    t.pu()
    t.home()
    mode('OBJECT')

    return trimmer


def create_b_trimmer(dim):
    turtle = bpy.context.scene.cursor
    t = bpy.ops.turtle
    buffer = bpy.context.scene.mt_trim_buffer

    t.add_turtle()
    t.pu()

    trimmer = bpy.context.object

    t.setp(v=dim['loc_A'])
    t.bk(d=0.5)
    t.lf(d=buffer)
    t.dn(d=0.5)
    t.pd()
    t.add_vert()
    t.up(d=dim['height'] + 1)
    t.select_all()
    t.fd(d=dim['b'] + 1)
    t.select_all()
    t.lf(d=1)
    t.pu()
    t.home()
    mode('OBJECT')

    return trimmer


# works for rectangular floors and straight walls
def create_tile_trimmers(tile_properties):
    mode('OBJECT')
    deselect_all()

    cursor = bpy.context.scene.cursor
    cursor_orig_location = cursor.location.copy()

    # create a cuboid the size of our tile and center it to use
    # as our bounding box for entire tile
    if tile_properties['base_blueprint'] is not 'NONE':
        bbox_proxy = draw_cuboid(Vector((
            tile_properties['tile_size'][0],
            tile_properties['base_size'][1],
            tile_properties['tile_size'][2])))
    else:
        bbox_proxy = draw_cuboid(tile_properties['tile_size'])
    mode('OBJECT')

    bbox_proxy.location = (
        bbox_proxy.location[0] - bbox_proxy.dimensions[0] / 2,
        bbox_proxy.location[1] - bbox_proxy.dimensions[1] / 2,
        bbox_proxy.location[2])

    cursor.location = cursor_orig_location
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

    # get bounding box and dimensions of cuboid
    bound_box = bbox_proxy.bound_box
    dimensions = bbox_proxy.dimensions.copy()

    # create trimmers
    buffer = bpy.context.scene.mt_trim_buffer
    x_neg_trimmer = create_x_neg_trimmer(bound_box, dimensions, buffer)
    x_neg_trimmer.name = tile_properties['tile_name'] + '.x_neg_trimmer'
    x_pos_trimmer = create_x_pos_trimmer(bound_box, dimensions, buffer)
    x_pos_trimmer.name = tile_properties['tile_name'] + '.x_pos_trimmer'
    y_neg_trimmer = create_y_neg_trimmer(bound_box, dimensions, buffer)
    y_neg_trimmer.name = tile_properties['tile_name'] + '.y_neg_trimmer'
    y_pos_trimmer = create_y_pos_trimmer(bound_box, dimensions, buffer)
    y_pos_trimmer.name = tile_properties['tile_name'] + '.y_pos_trimmer'
    z_pos_trimmer = create_z_pos_trimmer(bound_box, dimensions, buffer)
    z_pos_trimmer.name = tile_properties['tile_name'] + '.z_pos_trimmer'
    z_neg_trimmer = create_z_neg_trimmer(bound_box, dimensions, buffer)
    z_neg_trimmer.name = tile_properties['tile_name'] + '.z_neg_trimmer'

    trimmers = {
        'x_neg': x_neg_trimmer,
        'x_pos': x_pos_trimmer,
        'y_neg': y_neg_trimmer,
        'y_pos': y_pos_trimmer,
        'z_pos': z_pos_trimmer,
        'z_neg': z_neg_trimmer
    }

    cursor.location = cursor_orig_location

    for trimmer in trimmers.values():
        trimmer.display_type = 'BOUNDS'
        select(trimmer.name)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        trimmer.hide_viewport = True
        trimmer.parent = bpy.context.scene.objects[tile_properties['empty_name']]

    bpy.ops.object.delete({"selected_objects": [bbox_proxy]})
    return trimmers


def trim_side(obj, trimmer, buffer):
    boolean = obj.modifiers.new(trimmer.name + '_trimmer', 'BOOLEAN')
    boolean.operation = 'DIFFERENCE'
    boolean.object = trimmer
    trimmer.parent = obj
    trimmer.display_type = 'BOUNDS'
    trimmer.hide_viewport = True


def create_x_neg_trimmer(bound_box, dimensions, buffer):
    deselect_all()

    front_bottom_left = bound_box[0]

    t = bpy.ops.turtle

    t.add_turtle()
    t.pu()
    t.set_position(v=Vector((front_bottom_left)))
    t.ri(d=buffer)
    t.dn(d=0.5)
    t.bk(d=0.5)
    t.pd()
    t.fd(d=dimensions[1] + 1)
    t.select_all()
    t.up(d=dimensions[2] + 1)
    t.select_all()
    t.lf(d=0.5)
    t.select_all()
    bpy.ops.mesh.normals_make_consistent()
    mode('OBJECT')
    return bpy.context.object


def create_x_pos_trimmer(bound_box, dimensions, buffer):
    deselect_all()

    front_bottom_right = bound_box[4]

    t = bpy.ops.turtle

    t.add_turtle()
    t.pu()
    t.set_position(v=Vector((front_bottom_right)))
    t.lf(d=buffer)
    t.dn(d=0.5)
    t.bk(d=0.5)
    t.pd()
    t.fd(d=dimensions[1] + 1)
    t.select_all()
    t.up(d=dimensions[2] + 1)
    t.select_all()
    t.ri(d=0.5)
    t.select_all()
    bpy.ops.mesh.normals_make_consistent()
    mode('OBJECT')
    return bpy.context.object


def create_y_neg_trimmer(bound_box, dimensions, buffer):
    deselect_all()

    front_bottom_left = bound_box[0]
    t = bpy.ops.turtle

    t.add_turtle()
    t.pu()
    t.set_position(v=Vector((front_bottom_left)))
    t.fd(d=buffer)
    t.lf(d=0.5)
    t.dn(d=0.5)
    t.pd()
    t.ri(d=dimensions[0] + 1)
    t.select_all()
    t.bk(d=0.5)
    t.select_all()
    t.up(d=dimensions[2] + 1)
    t.select_all()
    bpy.ops.mesh.normals_make_consistent()
    mode('OBJECT')
    return bpy.context.object


def create_y_pos_trimmer(bound_box, dimensions, buffer):
    deselect_all()

    front_bottom_left = bound_box[0]
    t = bpy.ops.turtle

    t.add_turtle()
    t.pu()
    t.set_position(v=Vector((front_bottom_left)))
    t.fd(d=dimensions[1])
    t.bk(d=buffer)
    t.lf(d=0.5)
    t.dn(d=0.5)
    t.pd()
    t.ri(d=dimensions[0] + 1)
    t.select_all()
    t.fd(d=0.5)
    t.select_all()
    t.up(d=dimensions[2] + 1)
    t.select_all()
    bpy.ops.mesh.normals_make_consistent()
    mode('OBJECT')
    return bpy.context.object


def create_z_pos_trimmer(bound_box, dimensions, buffer):
    deselect_all()

    front_top_left = bound_box[2]
    t = bpy.ops.turtle

    t.add_turtle()
    t.pu()
    t.set_position(v=Vector((front_top_left)))
    t.dn(d=buffer)
    t.lf(d=0.5)
    t.bk(d=1)
    t.pd()
    t.fd(d=dimensions[1] + 1)
    t.select_all()
    t.ri(d=dimensions[0] + 1)
    t.select_all()
    t.up(d=0.5)
    t.select_all()
    bpy.ops.mesh.normals_make_consistent()
    mode('OBJECT')
    return bpy.context.object


def create_z_neg_trimmer(bound_box, dimensions, buffer):

    deselect_all()

    front_bottom_left = bound_box[0]
    t = bpy.ops.turtle

    t.add_turtle()
    t.pu()
    t.set_position(v=Vector((front_bottom_left)))
    t.up(d=buffer)
    t.lf(d=0.5)
    t.bk(d=0.5)
    t.pd()
    t.fd(d=dimensions[1] + 1)
    t.select_all()
    t.ri(d=dimensions[0] + 1)
    t.select_all()
    t.dn(d=0.5)
    t.select_all()
    bpy.ops.mesh.normals_make_consistent()
    mode('OBJECT')
    return bpy.context.object