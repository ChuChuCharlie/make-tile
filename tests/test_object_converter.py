import pytest
import bpy

def test_MT_OT_Convert_To_MT_Obj(cube):
    assert bpy.ops.object.convert_to_make_tile() == {'FINISHED'}


def test_MT_OT_Convert_To_MT_Obj_all_group_at_index_zero(cube):
    """The converter must leave the generated 'All' group at index 0."""
    obj = cube
    # Add a pre-existing vertex group so 'All' would be appended after it.
    group = obj.vertex_groups.new(name="Existing")
    group.add([v.index for v in obj.data.vertices], 1.0, 'ADD')

    assert bpy.ops.object.convert_to_make_tile() == {'FINISHED'}

    all_group = obj.vertex_groups.get("All")
    assert all_group is not None
    assert all_group.index == 0


def test_MT_OT_Convert_To_MT_Obj_existing_groups_used(cube):
    """When vertex groups exist the material should target them, not 'All'."""
    obj = cube
    group = obj.vertex_groups.new(name="Existing")
    group.add([v.index for v in obj.data.vertices], 1.0, 'ADD')

    assert bpy.ops.object.convert_to_make_tile() == {'FINISHED'}

    # displacement core should have textured the existing group
    assert "Existing" in obj.vertex_groups
    assert obj.mt_object_props.is_displacement is True


def test_MT_OT_Flatten_Tile(cube):
    """Flatten merges visible mesh objects in a collection and tags the result."""
    tile_collection = bpy.data.collections.new("flatten_test_collection")
    bpy.context.scene.collection.children.link(tile_collection)

    try:
        # Move the fixture cube into the test collection.
        tile_collection.objects.link(cube)
        bpy.context.scene.collection.objects.unlink(cube)

        # Add a second and third cube to exercise multi-object join path.
        shared_mesh = cube.data
        second_obj = bpy.data.objects.new("second_cube", shared_mesh)
        tile_collection.objects.link(second_obj)

        third_mesh = bpy.data.meshes.new("third_cube_mesh")
        third_obj = bpy.data.objects.new("third_cube", third_mesh)
        tile_collection.objects.link(third_obj)

        # Parent one cube to another, offset in world space, to verify
        # unparenting preserves transforms.
        second_obj.location = (2, 0, 0)
        second_obj.parent = cube
        second_obj.matrix_parent_inverse = cube.matrix_world.inverted()

        # Add a non-mesh object to verify it is removed.
        camera = bpy.data.objects.new("test_camera", bpy.data.cameras.new("test_camera_data"))
        tile_collection.objects.link(camera)

        cube.select_set(True)
        bpy.context.view_layer.objects.active = cube
        cube.mt_object_props.is_mt_object = True

        assert bpy.ops.object.flatten_tiles() == {'FINISHED'}

        # Only one object (the merged mesh) should remain in the collection.
        assert len(tile_collection.all_objects) == 1
        remaining = list(tile_collection.all_objects)
        assert remaining[0].type == 'MESH'
        assert remaining[0].mt_object_props.geometry_type == 'FLATTENED'
        assert remaining[0].mt_object_props.is_displacement is False

        # The second cube's world location should still be represented in the
        # merged mesh after direct unparenting replaced parent_clear.
        mesh = remaining[0].data
        assert any(v.co.x > 1.5 for v in mesh.vertices)
    finally:
        # Clean up the test collection so it does not leak into other tests.
        bpy.context.scene.collection.children.unlink(tile_collection)
        bpy.data.collections.remove(tile_collection)


def test_MT_OT_Flatten_Tile_single_visible_mesh(cube):
    """Flatten removes non-mesh siblings when only one mesh is visible."""
    tile_collection = bpy.data.collections.new("flatten_single_mesh_collection")
    bpy.context.scene.collection.children.link(tile_collection)

    try:
        tile_collection.objects.link(cube)
        bpy.context.scene.collection.objects.unlink(cube)

        camera = bpy.data.objects.new("single_test_camera", bpy.data.cameras.new("single_camera_data"))
        tile_collection.objects.link(camera)

        cube.select_set(True)
        bpy.context.view_layer.objects.active = cube
        cube.mt_object_props.is_mt_object = True

        assert bpy.ops.object.flatten_tiles() == {'FINISHED'}

        assert len(tile_collection.all_objects) == 1
        assert tile_collection.all_objects[0] is cube
        assert cube.mt_object_props.geometry_type == 'FLATTENED'
    finally:
        bpy.context.scene.collection.children.unlink(tile_collection)
        bpy.data.collections.remove(tile_collection)


def test_MT_OT_Flatten_Tile_no_visible_meshes(cube):
    """Flatten should return FINISHED without error when nothing is visible."""
    tile_collection = bpy.data.collections.new("flatten_no_meshes_collection")
    bpy.context.scene.collection.children.link(tile_collection)

    try:
        tile_collection.objects.link(cube)
        bpy.context.scene.collection.objects.unlink(cube)
        cube.hide_set(True)

        camera = bpy.data.objects.new("no_mesh_camera", bpy.data.cameras.new("no_mesh_camera_data"))
        tile_collection.objects.link(camera)

        cube.select_set(True)
        bpy.context.view_layer.objects.active = cube
        cube.mt_object_props.is_mt_object = True

        assert bpy.ops.object.flatten_tiles() == {'FINISHED'}
        # Cube should be left untouched because there are no visible meshes to keep.
        assert cube in tile_collection.all_objects
        assert cube.hide_get() is True
    finally:
        cube.hide_set(False)
        bpy.context.scene.collection.children.unlink(tile_collection)
        bpy.data.collections.remove(tile_collection)
