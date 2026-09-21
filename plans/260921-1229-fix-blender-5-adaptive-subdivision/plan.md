# Fix Plan: Blender 5 adaptive subdivision error

## Context

Issue [#3](https://github.com/ChuChuCharlie/make-tile/issues/3) reports an `AttributeError` when creating roof tiles in Blender 5:

```
AttributeError: 'CyclesObjectSettings' object has no attribute 'use_adaptive_subdivision'
```

The traceback points to `add_subsurf_modifier()` in `MakeTile/tile_creation/create_tile.py:830`, which currently does:

```python
obj.cycles.use_adaptive_subdivision = True
```

## Root Cause

Blender 5.0 removed the per-object Cycles property `CyclesObjectSettings.use_adaptive_subdivision`. Adaptive subdivision is now a property of the **Subdivision Surface modifier**:

- Blender 4.x/4.2: `obj.cycles.use_adaptive_subdivision = True` (Cycles experimental feature)
- Blender 5.0+: `subsurf_mod.use_adaptive_subdivision = True` on the `SUBSURF` modifier

Sources:

- [Blender 5.0 Python API Change Log – removed `CyclesObjectSettings.use_adaptive_subdivision`](https://docs.blender.org/api/5.0/change_log.html)
- [Blender 5.0 Cycles release notes – adaptive subdivision moved to Subdivision Surface modifier](https://developer.blender.org/docs/release_notes/5.0/cycles/)
- [Blender 4.2 SubsurfModifier API – no `use_adaptive_subdivision`](https://docs.blender.org/api/4.2/bpy.types.SubsurfModifier.html)
- [Latest SubsurfModifier API – includes `use_adaptive_subdivision`](https://docs.blender.org/api/latest/bpy.types.SubsurfModifier.html)

## Scope

A helper should be added so all call sites can enable adaptive subdivision safely across Blender 4 and 5.

Files affected:

- `MakeTile/tile_creation/create_tile.py` — `add_subsurf_modifier()`
- `MakeTile/materials/materials.py` — `add_preview_mesh_subsurf()`
- `MakeTile/operators/return_to_preview.py` — `set_to_preview()`

## Proposed Fix

Add a small cross-version helper in `create_tile.py`:

```python
def enable_adaptive_subdivision(obj, subsurf_mod=None):
    """Enable adaptive subdivision in a Blender 4/5 compatible way.

    Blender 5.0 moved the adaptive-subdivision toggle from
    `obj.cycles.use_adaptive_subdivision` to the Subdivision Surface modifier.
    This helper uses whichever path is available.
    """
    if subsurf_mod is not None and hasattr(subsurf_mod, 'use_adaptive_subdivision'):
        subsurf_mod.use_adaptive_subdivision = True
        return

    if hasattr(obj.cycles, 'use_adaptive_subdivision'):
        obj.cycles.use_adaptive_subdivision = True
```

Then update the three call sites:

### 1. `add_subsurf_modifier()` in `create_tile.py`

```python
def add_subsurf_modifier(obj):
    subsurf = obj.modifiers.new('MT Subsurf', 'SUBSURF')
    subsurf.subdivision_type = 'SIMPLE'
    obj.mt_object_props.subsurf_mod_name = subsurf.name
    enable_adaptive_subdivision(obj, subsurf)
    return subsurf.name
```

### 2. `add_preview_mesh_subsurf()` in `materials/materials.py`

```python
def add_preview_mesh_subsurf(obj):
    obj_subsurf = obj.modifiers.new('Subsurf', 'SUBSURF')
    obj_subsurf.subdivision_type = 'SIMPLE'
    obj_subsurf.levels = 0
    enable_adaptive_subdivision(obj, obj_subsurf)
    bpy.context.scene.cycles.preview_dicing_rate = 1
```

### 3. `set_to_preview()` in `operators/return_to_preview.py`

```python
try:
    if (bpy.context.scene.render.engine != 'CYCLES'
            or v3d.shading.type != 'RENDERED'):
        subsurf = obj.modifiers[props.subsurf_mod_name]
        subsurf.show_viewport = False
        enable_adaptive_subdivision(obj, subsurf)
except KeyError:
    pass
```

`scene.cycles.preview_dicing_rate` is unchanged because it still exists in Blender 5.

## Implementation Steps

1. Add `enable_adaptive_subdivision()` to `MakeTile/tile_creation/create_tile.py`.
2. Update `add_subsurf_modifier()` to call the helper.
3. Import the helper in `MakeTile/materials/materials.py` and update `add_preview_mesh_subsurf()`.
4. Import the helper in `MakeTile/operators/return_to_preview.py` and update `set_to_preview()`.
5. Run `python -m py_compile` on the three modified files.
6. Smoke-test by creating a roof tile in Blender 5.

## Success Criteria

- Roof tile creation no longer raises `AttributeError: 'CyclesObjectSettings' object has no attribute 'use_adaptive_subdivision'` in Blender 5.
- Adaptive subdivision is still enabled in Blender 4.x (backward compatibility).
- Preview mesh and return-to-preview workflows do not regress.

## Risk Assessment

- **Low risk.** All changes are guarded by `hasattr` checks, so they degrade gracefully on either Blender version.
- No algorithmic changes; only the location of the adaptive-subdivision toggle is abstracted.

## Next Steps

- Implement the helper and update the three call sites.
- Run compile checks and Blender smoke tests.
