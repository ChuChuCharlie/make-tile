import pytest
import bpy


@pytest.mark.parametrize(
    "leg_1_len, leg_2_len, angle",
    [
        (0.5, 0.5, 90),
        (1.0, 1.0, 90),
        (1.5, 1.5, 90),
        (2.0, 2.0, 90),
        (1.0, 2.5, 90),
        (2.5, 1.0, 90),
        (1.5, 2.5, 90),
        (2.5, 1.5, 90),
        (0.5, 3.0, 90),
        (3.0, 0.5, 90),
        (0.5, 3.5, 90),
        (3.5, 0.5, 90),
        (1.0, 5.0, 90),
        (5.0, 1.0, 90),
        (0.5, 0.5, 60),
        (1.0, 1.0, 60),
        (1.5, 1.5, 60),
        (2.0, 2.0, 60),
        (1.0, 2.5, 60),
        (2.5, 1.0, 60),
        (0.5, 3.0, 60),
        (3.0, 0.5, 60),
    ])
def test_triangular_floor_small_legs_no_crash(
        fake_context, leg_1_len, leg_2_len, angle):
    """Issue #29: triangular floor tiles must not crash for short legs."""
    scene = fake_context.get('scene')
    scene_props = scene.mt_scene_props
    scene_props.tile_type = "TRIANGULAR_FLOOR"

    op = bpy.ops.object.make_triangular_floor(
        fake_context,
        refresh=True,
        base_blueprint='OPENLOCK',
        main_part_blueprint='PLAIN',
        leg_1_len=leg_1_len,
        leg_2_len=leg_2_len,
        angle=angle)

    assert op == {'FINISHED'}


@pytest.mark.parametrize(
    "leg_1_len, leg_2_len, expected_cutters",
    [
        # No cutters at all when both legs are <= 1.5.
        (0.5, 0.5, 0),
        (1.0, 1.0, 0),
        (1.5, 1.5, 0),
        # Isosceles right triangle: Leg 1 + Leg 2 + hypotenuse + slot.
        (2.0, 2.0, 4),
        # Small isosceles right triangle: slot + hypotenuse, no leg cutters.
        (1.6, 1.6, 2),
        # Asymmetric cases: short leg (<=1.5) gets no cutter. Long leg gets
        # floor(leg) - 1 cutters. Slot only when both legs are at least 1.5.
        (1.0, 2.0, 1),    # leg 2: 1 cutter; no slot
        (2.0, 1.0, 1),    # leg 1: 1 cutter; no slot
        (1.0, 2.5, 1),    # leg 2: 1 cutter; no slot
        (2.5, 1.0, 1),    # leg 1: 1 cutter; no slot
        (1.5, 2.0, 2),    # leg 2: 1 cutter + slot
        (2.0, 1.5, 2),    # leg 1: 1 cutter + slot
        (1.5, 2.5, 2),    # leg 2: 1 cutter + slot
        (2.5, 1.5, 2),    # leg 1: 1 cutter + slot
        (1.0, 3.0, 2),    # leg 2: 2 cutters; no slot
        (3.0, 1.0, 2),    # leg 1: 2 cutters; no slot
        (1.0, 3.5, 2),    # leg 2: 2 cutters; no slot
        (3.5, 1.0, 2),    # leg 1: 2 cutters; no slot
        (1.5, 3.0, 3),    # leg 2: 2 cutters + slot
        (3.0, 1.5, 3),    # leg 1: 2 cutters + slot
        (1.5, 3.5, 3),    # leg 2: 2 cutters + slot
        (3.5, 1.5, 3),    # leg 1: 2 cutters + slot
        (1.0, 4.0, 3),    # leg 2: 3 cutters; no slot
        (4.0, 1.0, 3),    # leg 1: 3 cutters; no slot
        (1.0, 4.5, 3),    # leg 2: 3 cutters; no slot
        (4.5, 1.0, 3),    # leg 1: 3 cutters; no slot
        (1.0, 5.0, 4),    # leg 2: 4 cutters; no slot
        (5.0, 1.0, 4),    # leg 1: 4 cutters; no slot
    ])
def test_triangular_floor_cutter_counts(
        fake_context, leg_1_len, leg_2_len, expected_cutters):
    """Issue #29: verify cutter counts at 90 degrees."""
    scene = fake_context.get('scene')
    scene_props = scene.mt_scene_props
    scene_props.tile_type = "TRIANGULAR_FLOOR"

    op = bpy.ops.object.make_triangular_floor(
        fake_context,
        refresh=True,
        base_blueprint='OPENLOCK',
        main_part_blueprint='PLAIN',
        leg_1_len=leg_1_len,
        leg_2_len=leg_2_len,
        angle=90)

    assert op == {'FINISHED'}

    tile_collection = _get_latest_tile_collection(scene, 'triangular_floor')
    assert tile_collection is not None

    base = next(
        (obj for obj in tile_collection.objects if obj.name.endswith('.base')),
        None)
    assert base is not None

    cutter_count = _count_clip_cutters(base)
    assert cutter_count == expected_cutters, (
        f"Expected {expected_cutters} cutters for "
        f"{leg_1_len}x{leg_2_len} tile, found {cutter_count}")

    # The slot cutter is only added when both legs are at least 1.5.
    slot_count = _count_slot_cutters(base)
    if leg_1_len >= 1.5 and leg_2_len >= 1.5:
        assert slot_count == 1, (
            f"Expected 1 slot cutter for {leg_1_len}x{leg_2_len} tile, "
            f"found {slot_count}")
    else:
        assert slot_count == 0, (
            f"Expected 0 slot cutters for {leg_1_len}x{leg_2_len} tile, "
            f"found {slot_count}")


@pytest.mark.parametrize(
    "leg_1_len, leg_2_len, angle",
    [
        (0.3, 0.3, 90),
        (0.4, 2.0, 90),
        (2.0, 0.3, 90),
        (2.0, 2.0, 1),
        (2.0, 2.0, 179),
    ])
def test_triangular_floor_property_clamping(
        fake_context, leg_1_len, leg_2_len, angle):
    """Values below the property minimums are clamped, not rejected."""
    scene = fake_context.get('scene')
    scene_props = scene.mt_scene_props
    scene_props.tile_type = "TRIANGULAR_FLOOR"

    op = bpy.ops.object.make_triangular_floor(
        fake_context,
        refresh=True,
        base_blueprint='OPENLOCK',
        main_part_blueprint='PLAIN',
        leg_1_len=leg_1_len,
        leg_2_len=leg_2_len,
        angle=angle)

    assert op == {'FINISHED'}

    tile_collection = _get_latest_tile_collection(scene, 'triangular_floor')
    assert tile_collection is not None
    tile_props = tile_collection.mt_tile_props
    assert tile_props.leg_1_len >= 0.5, (
        f"leg_1_len was not clamped: {tile_props.leg_1_len}")
    assert tile_props.leg_2_len >= 0.5, (
        f"leg_2_len was not clamped: {tile_props.leg_2_len}")
    assert 1 <= tile_props.angle <= 179, (
        f"angle was not clamped: {tile_props.angle}")


def _get_latest_tile_collection(scene, tile_type_name):
    """Return the most recently created tile collection for this scene."""
    tiles_collection = next(
        (c for c in scene.collection.children if c.name == 'Tiles'),
        None)
    if tiles_collection is None:
        return None
    candidates = [
        c for c in tiles_collection.children
        if c.name.startswith(tile_type_name)]
    return candidates[-1] if candidates else None


def _count_clip_cutters(base_obj):
    """Count OpenLOCK base cutters linked to the base via booleans."""
    return sum(
        1
        for mod in base_obj.modifiers
        if mod.type == 'BOOLEAN'
        and mod.operation == 'DIFFERENCE'
        and mod.object is not None
        and ('Cutter' in mod.object.name or 'Slot' in mod.object.name))


def _count_slot_cutters(base_obj):
    """Count slot cutters linked to the base via booleans."""
    return sum(
        1
        for mod in base_obj.modifiers
        if mod.type == 'BOOLEAN'
        and mod.operation == 'DIFFERENCE'
        and mod.object is not None
        and 'Slot' in mod.object.name)
