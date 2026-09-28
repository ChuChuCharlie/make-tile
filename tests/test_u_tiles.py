import pytest
import bpy


@pytest.mark.parametrize("main_part_blueprint, base_blueprint, operator_return",
                         [('OPENLOCK', 'OPENLOCK', {'FINISHED'}),
                          ('OPENLOCK', 'PLAIN', {'FINISHED'}),
                          ('OPENLOCK', 'OPENLOCK_S_WALL', {'FINISHED'}),
                          ('OPENLOCK', 'PLAIN_S_WALL', {'FINISHED'}),
                          ('OPENLOCK', 'NONE', {'FINISHED'}),
                          ('PLAIN', 'PLAIN', {'FINISHED'}),
                          ('PLAIN', 'OPENLOCK', {'FINISHED'}),
                          ('PLAIN', 'NONE', {'FINISHED'}),
                          ('NONE', 'NONE', {'FINISHED'})])
def test_Make_U_Wall_OT_types(fake_context, main_part_blueprint, base_blueprint, operator_return):
    """U-Wall operator must instantiate without __init__ argument errors."""
    scene = fake_context.get('scene')
    scene_props = scene.mt_scene_props
    scene_props.tile_type = "U_WALL"
    op = bpy.ops.object.make_u_wall(
        fake_context,
        refresh=True,
        main_part_blueprint=main_part_blueprint,
        base_blueprint=base_blueprint)
    assert op == operator_return


@pytest.mark.parametrize("main_part_blueprint, base_blueprint, wall_position",
                         [('PLAIN', 'PLAIN', 'SIDE'),
                          ('PLAIN', 'OPENLOCK', 'SIDE'),
                          ('PLAIN', 'PLAIN', 'EXTERIOR'),
                          ('PLAIN', 'OPENLOCK', 'EXTERIOR'),
                          ('OPENLOCK', 'PLAIN', 'SIDE'),
                          ('OPENLOCK', 'OPENLOCK', 'SIDE'),
                          ('OPENLOCK', 'PLAIN', 'EXTERIOR'),
                          ('OPENLOCK', 'OPENLOCK', 'EXTERIOR')])
def test_u_wall_bottom_vertex_groups(fake_context, main_part_blueprint, base_blueprint, wall_position):
    """Bottom vertex groups must be populated after removing shortest-path selection.

    Covers PLAIN and OPENLOCK main parts, PLAIN/OPENLOCK bases, and
    SIDE/EXTERIOR wall positions to ensure the bottom-Z calculation is correct
    in all configurations.
    """
    scene = fake_context.get('scene')
    scene_props = scene.mt_scene_props
    scene_props.tile_type = "U_WALL"

    op = bpy.ops.object.make_u_wall(
        fake_context,
        refresh=True,
        main_part_blueprint=main_part_blueprint,
        base_blueprint=base_blueprint,
        wall_position=wall_position)
    assert op == {'FINISHED'}

    tile_collection = bpy.data.collections.get('u_wall')
    assert tile_collection is not None
    core = next(
        (obj for obj in tile_collection.objects if obj.name.endswith('.core')),
        None)
    assert core is not None

    bottom_groups = ('Leg 1 Bottom', 'Leg 2 Bottom', 'End Wall Bottom')
    for group_name in bottom_groups:
        vg = core.vertex_groups.get(group_name)
        assert vg is not None, f"{group_name} missing on U-Wall core"
        assert len(vg.vertices) > 0, f"{group_name} is empty on U-Wall core"

    # Sanity check: top groups were derived from bottom groups.
    for group_name in ('Leg 1 Top', 'Leg 2 Top', 'End Wall Top'):
        vg = core.vertex_groups.get(group_name)
        assert vg is not None, f"{group_name} missing on U-Wall core"
        assert len(vg.vertices) > 0, f"{group_name} is empty on U-Wall core"
