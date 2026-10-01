import pytest
import bpy
import bmesh
from mathutils.bvhtree import BVHTree


@pytest.mark.parametrize("main_part_blueprint, base_blueprint, operator_return",
                         [('OPENLOCK', 'OPENLOCK', {'FINISHED'}),
                          ('OPENLOCK', 'PLAIN', {'FINISHED'}),
                          ('OPENLOCK', 'NONE', {'FINISHED'}),
                          ('OPENLOCK', 'OPENLOCK_S_WALL', {'FINISHED'}),
                          ('OPENLOCK', 'PLAIN_S_WALL', {'FINISHED'}),
                          ('PLAIN', 'PLAIN', {'FINISHED'}),
                          ('PLAIN', 'OPENLOCK', {'FINISHED'}),
                          ('PLAIN', 'NONE', {'FINISHED'}),
                          ('NONE', 'NONE', {'FINISHED'})])
def test_MT_OT_Make_L_Wall_Tile_types(fake_context, main_part_blueprint, base_blueprint, operator_return):
    scene = fake_context.get('scene')
    scene_props = scene.mt_scene_props
    scene_props.tile_type = "L_WALL"
    op = bpy.ops.object.make_l_wall_tile(
        fake_context,
        refresh=True,
        main_part_blueprint=main_part_blueprint,
        base_blueprint=base_blueprint)
    assert op == operator_return


def test_l_wall_top_pegs_clear_corner(fake_context):
    """Top pegs on long L-wall legs must sit on the wall top, not the corner."""
    scene = fake_context.get('scene')
    scene_props = scene.mt_scene_props
    scene_props.tile_type = "L_WALL"

    op = bpy.ops.object.make_l_wall_tile(
        fake_context,
        refresh=True,
        main_part_blueprint='OPENLOCK',
        base_blueprint='OPENLOCK',
        leg_1_len=6.0,
        leg_2_len=6.0,
        tile_x=0.5,
        tile_y=0.5,
        tile_z=2.0,
        base_x=6.0,
        base_y=0.5,
        base_z=0.3,
        angle=90)
    assert op == {'FINISHED'}

    tile_name = 'l_wall'
    core = bpy.data.objects.get(tile_name + '.core')
    assert core is not None, "Wall core was not created"

    depsgraph = bpy.context.evaluated_depsgraph_get()
    core_eval = core.evaluated_get(depsgraph)
    core_mesh = core_eval.to_mesh()
    bm_core = bmesh.new()
    bm_core.from_mesh(core_mesh)
    bm_core.normal_update()
    bvh = BVHTree.FromBMesh(bm_core, epsilon=0.001)
    core_eval.to_mesh_clear()
    bm_core.free()

    # The bottom-centre of each peg should be inside the core.
    pegs = [obj for obj in bpy.data.objects if obj.name.startswith('Leg 1 Peg') or obj.name.startswith('Leg 2 Peg')]
    assert len(pegs) >= 2, "Expected top pegs for both legs"

    for peg in pegs:
        peg_eval = peg.evaluated_get(depsgraph)
        peg_mesh = peg_eval.to_mesh()
        bm_peg = bmesh.new()
        bm_peg.from_mesh(peg_mesh)
        bm_peg.normal_update()

        # Sample the lowest Z vertex of the evaluated peg as the contact point.
        min_z = min(v.co.z for v in bm_peg.verts)
        sample_points = [v.co for v in bm_peg.verts if abs(v.co.z - min_z) < 0.001]
        assert sample_points, "Could not sample peg bottom vertices"

        inside_count = 0
        for point in sample_points:
            _, normal, _, _ = bvh.find_nearest(point)
            if normal is not None:
                # Point is inside the manifold if the vector from nearest surface
                # to the point points against the normal.
                p2 = point - (point - normal * 0.0001)
                # Use a simpler inside test: nearest surface should be the point
                # itself if it is on the surface, otherwise sign of dot.
                nearest, n, _, _ = bvh.find_nearest(point)
                if n is not None and (point - nearest).dot(n) >= -0.001:
                    inside_count += 1

        assert inside_count >= len(sample_points) * 0.9, (
            f"Peg {peg.name} has vertices outside the wall core near the corner")

        peg_eval.to_mesh_clear()
        bm_peg.free()
