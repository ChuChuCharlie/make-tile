# Fix Plan: Blender 5 bake settings migration

## Context

Testing **Export Tile** in Blender 5 raised:

```
AttributeError: 'RenderSettings' object has no attribute 'bake_type'
```

At [bakedisplacement.py:251](MakeTile/operators/bakedisplacement.py#L251):

```python
context.scene.render.bake_type = 'DISPLACEMENT'
```

## Root Cause

Blender 5.0 removed bake properties from `RenderSettings` and moved them to a new `BakeSettings` object under `scene.render.bake`.

- Blender 4.2/4.5: `scene.render.bake_type`, `scene.render.bake_margin`
- Blender 5.0+: `scene.render.bake.type`, `scene.render.bake.margin`

In addition, `CyclesRenderSettings.bake_type` was used in older code but may not exist in some Blender versions; the modern cross-version path is `scene.render.bake.type`.

Sources:

- [Blender 5.0 API Change Log – RenderSettings bake removals](https://docs.blender.org/api/5.0/change_log.html)
- [Blender 5.0 BakeSettings API](https://docs.blender.org/api/5.0/bpy.types.BakeSettings.html)
- [Blender 4.2 RenderSettings API – still has bake_type](https://docs.blender.org/api/4.2/bpy.types.RenderSettings.html)

## Proposed Fix

Add a small helper to access `bake_type` and `bake_margin` compatibly:

```python
def set_bake_setting(scene, attr, value):
    """Set a bake property on scene.render, handling the Blender 5 migration.

    Blender 5.0 moved bake settings from scene.render.* to scene.render.bake.*.
    This helper writes to the new path when it exists, otherwise to the old path.
    """
    bake = getattr(scene.render, 'bake', None)
    if bake is not None and hasattr(bake, attr):
        setattr(bake, attr, value)
    else:
        setattr(scene.render, attr, value)


def get_bake_setting(scene, attr):
    """Read a bake property from scene.render, handling the Blender 5 migration."""
    bake = getattr(scene.render, 'bake', None)
    if bake is not None and hasattr(bake, attr):
        return getattr(bake, attr)
    return getattr(scene.render, attr)
```

Then update [bakedisplacement.py](MakeTile/operators/bakedisplacement.py):

- Replace `context.scene.cycles.bake_type` reads/writes with `get_bake_setting`/`set_bake_setting`.
- Replace `context.scene.render.bake_type` write with `set_bake_setting`.
- Replace `context.scene.render.bake_margin` write with `set_bake_setting`.

Concrete replacements:

```python
# set_cycles_to_bake_mode
cycles_settings = {
    ...
    'orig_bake_type': get_bake_setting(context.scene, 'type'),
    ...
}
...
set_bake_setting(context.scene, 'type', 'EMIT')
```

```python
# reset_renderer_from_bake
set_bake_setting(context.scene, 'type', orig_settings['orig_bake_type'])
```

```python
# bake_displacement_map
set_bake_setting(context.scene, 'type', 'DISPLACEMENT')
set_bake_setting(context.scene, 'margin', 10)
```

Note: the code calls `bpy.ops.object.bake(type='EMIT')`. In Blender 5 the `type` operator argument may require `bake.type` to be set, or the operator may accept it directly. We keep the operator call as-is because it still works with the `EMIT` keyword in Blender 5 bake operator; the important part is ensuring `scene.render.bake.type` is set consistently.

## Implementation Steps

1. Add `set_bake_setting()` and `get_bake_setting()` to [bakedisplacement.py](MakeTile/operators/bakedisplacement.py) near the top.
2. Replace all `context.scene.cycles.bake_type` and `context.scene.render.bake_type`/`bake_margin` accesses with the helpers.
3. Run `python -m py_compile`.
4. Re-test export tile / make 3D in Blender 5.

## Success Criteria

- No `AttributeError` during displacement baking in Blender 5.
- Bake type is restored correctly after baking.
- Backward compatibility with Blender 4.x is maintained.

## Risk Assessment

- **Low risk.** Helpers degrade gracefully between API versions.
- Verify the `bpy.ops.object.bake(type='EMIT')` call still works in Blender 5; if not, additional operator argument updates may be needed.

## Next Steps

- Implement the helper and update all bake setting accesses.
- Re-test.
