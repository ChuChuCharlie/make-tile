# Fix Plan: Blender 5 displacement bake produces blank texture

## Context

After fixing the bake-setting migration errors, the **Export Tile** workflow no longer crashes, but the exported STL has no baked displacement. The baked displacement image appears blank/empty.

The relevant code is in `MakeTile/operators/bakedisplacement.py`, function `bake_displacement_map()`.

## Root Cause

The displacement-baking workflow does the following:

1. For each material on the object, it finds a `disp_emission` node, links its `Emission` output to the `Surface` input of `Material Output`, and disconnects the displacement output.
2. It assigns the new displacement image to a `disp_texture_node` image texture node.
3. It calls `bpy.ops.object.bake(type='EMIT')`.

In Blender 5, the bake system changed so that `bpy.ops.object.bake` requires:

- The target Image Texture node to be **selected** and **active** (`tree.nodes.active = texture_node`).
- The correct scene render target (`scene.render.bake.target = 'IMAGE_TEXTURES'`).

The current code assigns `texture_node.image = disp_image` but does **not** make the node active/selected, and does not explicitly set the bake target. In Blender 4.x this may have worked implicitly, but in Blender 5 it produces a blank bake.

Sources:

- [Blender 5.2 Render Baking manual](https://docs.blender.org/manual/en/latest/render/cycles/baking.html)
- [Blender StackExchange – baked textures are black](https://blender.stackexchange.com/questions/296469/blender-python-baked-texture-maps-are-black)
- [Blender StackExchange – how to bake emission](https://blender.stackexchange.com/questions/262416/how-can-i-bake-emission)

## Proposed Fix

Update `bake_displacement_map()` to explicitly:

1. Set `scene.render.bake.target = 'IMAGE_TEXTURES'` (when the property exists).
2. Make the `disp_texture_node` the active and selected node in each material node tree:
   - `texture_node.select = True`
   - `tree.nodes.active = texture_node`
3. Clear any existing pixel data before baking (`use_clear=True` or manually fill the image).

Implementation sketch:

```python
def bake_displacement_map(obj):
    ...
    # ensure we bake into image textures
    if hasattr(context.scene.render.bake, 'target'):
        context.scene.render.bake.target = 'IMAGE_TEXTURES'

    disp_materials = []
    mat_set = set()
    for item in obj.material_slots.items():
        if item[0]:
            material = bpy.data.materials[item[0]]
            tree = material.node_tree

            if 'disp_emission' in tree.nodes and material not in mat_set:
                disp_materials.append(material)
                mat_set.add(material)
                displacement_emission_node = tree.nodes['disp_emission']
                mat_output_node = tree.nodes['Material Output']

                tree.links.new(
                    displacement_emission_node.outputs['Emission'],
                    mat_output_node.inputs['Surface'])

                displacement_node = tree.nodes['final_disp']
                link = displacement_node.outputs[0].links[0]
                tree.links.remove(link)

                texture_node = tree.nodes['disp_texture_node']
                texture_node.image = disp_image
                texture_node.select = True
                tree.nodes.active = texture_node
    ...
```

Also ensure the bake call uses `use_clear=True` so old image data does not persist:

```python
bpy.ops.object.bake(type='EMIT', target='IMAGE_TEXTURES', use_clear=True)
```

Operator arguments must be validated against the current Blender version; `target` and `use_clear` are standard in Blender 5 but may differ in Blender 4.2.

## Implementation Steps

1. Read current `bakedisplacement.py` around `bake_displacement_map()`.
2. Add `scene.render.bake.target = 'IMAGE_TEXTURES'` guard.
3. Set `texture_node.select = True` and `tree.nodes.active = texture_node` after assigning the image.
4. Update the `bpy.ops.object.bake()` call to pass `target='IMAGE_TEXTURES'` and `use_clear=True` when supported.
5. Compile-check the file.
6. Re-test export tile and verify the displacement image is non-blank.

## Success Criteria

- Exported STL includes baked displacement geometry.
- `disp_image` contains non-blank pixel data after `bake_displacement_map()`.
- Blender 4.x compatibility preserved.

## Risk Assessment

- **Medium risk.** Baking behavior is version-sensitive. Need to guard new API paths and test on both Blender 4 and 5.
- The operator keyword `target` may need a fallback if Blender 4.2's `bake()` operator does not accept it.

## Next Steps

- Implement the fix in `bakedisplacement.py`.
- Re-test export tile in Blender 5.
