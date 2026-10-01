import pytest
import bpy
import bmesh
from mathutils.bvhtree import BVHTree


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


def _check_u_wall_pegs_inside_core(depsgraph, core):
    """Assert all evaluated top pegs for a U-wall sit on the wall core."""
    core_eval = core.evaluated_get(depsgraph)
    core_mesh = core_eval.to_mesh()
    bm_core = bmesh.new()
    bm_core.from_mesh(core_mesh)
    bm_core.normal_update()
    bvh = BVHTree.FromBMesh(bm_core, epsilon=0.001)
    core_eval.to_mesh_clear()
    bm_core.free()

    pegs = [
        obj for obj in bpy.data.objects
        if obj.name.startswith('End Wall Top Peg')
        or obj.name.startswith('Leg 1 Top Peg')
        or obj.name.startswith('Leg 2 Top Peg')]
    assert len(pegs) == 3, f"Expected exactly 3 top pegs, got {len(pegs)}"

    for peg in pegs:
        peg_eval = peg.evaluated_get(depsgraph)
        peg_mesh = peg_eval.to_mesh()
        bm_peg = bmesh.new()
        bm_peg.from_mesh(peg_mesh)
        bm_peg.normal_update()

        min_z = min(v.co.z for v in bm_peg.verts)
        sample_points = [v.co for v in bm_peg.verts if abs(v.co.z - min_z) < 0.001]
        assert sample_points, "Could not sample peg bottom vertices"

        inside_count = 0
        for point in sample_points:
            nearest, normal, _, _ = bvh.find_nearest(point)
            if normal is not None and (point - nearest).dot(normal) >= -0.001:
                inside_count += 1

        assert inside_count >= len(sample_points) * 0.9, (
            f"Peg {peg.name} has vertices outside the wall core")

        peg_eval.to_mesh_clear()
        bm_peg.free()


def test_u_wall_top_pegs_inside_core(fake_context):
    """Top pegs on long U-wall sides must sit on the wall core, not overhang.

    Uses the default wall thickness (tile_y=0.32, base_y=0.5) because that is
    the most common user configuration and the one most sensitive to the
    cross-offset calculation.
    """
    scene = fake_context.get('scene')
    scene_props = scene.mt_scene_props
    scene_props.tile_type = "U_WALL"

    # Blender 5.2 background mode does not accept the legacy positional-dict
    # context override used by the older tests, so we use temp_override here.
    with bpy.context.temp_override(**fake_context):
        op = bpy.ops.object.make_u_wall(
            refresh=True,
            main_part_blueprint='OPENLOCK',
            base_blueprint='OPENLOCK',
            wall_position='SIDE',
            leg_1_len=6.0,
            leg_2_len=6.0,
            tile_x=4.0,
            tile_y=0.32,
            tile_z=2.0,
            base_x=4.0,
            base_y=0.5,
            base_z=0.3)
        assert op == {'FINISHED'}

        depsgraph = bpy.context.evaluated_depsgraph_get()

    core = bpy.data.objects.get('u_wall.core')
    assert core is not None, "Wall core was not created"
    _check_u_wall_pegs_inside_core(depsgraph, core)
