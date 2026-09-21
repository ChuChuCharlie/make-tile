# Fix Plan: Blender 5 Cycles `feature_set` removal

## Context

Testing **Create Lighting Setup** in Blender 5.2 raised:

```
AttributeError: 'CyclesRenderSettings' object has no attribute 'feature_set'
```

At [create_lighting_setup.py:59](MakeTile/operators/create_lighting_setup.py#L59):

```python
context.scene.cycles.feature_set = 'EXPERIMENTAL'
```

## Root Cause

The `CyclesRenderSettings.feature_set` enum (`SUPPORTED` / `EXPERIMENTAL`) was removed in Blender 5.0. The only feature that required `EXPERIMENTAL` was **adaptive subdivision**, which is now always available in the Subdivision Surface modifier.

- Blender 4.5: `feature_set` exists; needed to enable adaptive subdivision.
- Blender 5.0+: `feature_set` removed; adaptive subdivision is built into the `SUBSURF` modifier.

Sources:

- [Blender 5.0 Cycles release notes](https://developer.blender.org/docs/release_notes/5.0/cycles/)
- [StackExchange – Feature Set option removed in Blender 5](https://stackoverflow.com/questions/344138/i-dont-have-the-feature-set-option-in-the-render-window-with-cycles)
- [Blender 4.5 Experimental Features manual](https://docs.blender.org/manual/nb/4.5/render/cycles/features.html)

## Proposed Fix

Guard the `feature_set` assignment so it only runs when the attribute exists. This preserves Blender 4.x behavior while ignoring it on Blender 5.

Change in [create_lighting_setup.py:59](MakeTile/operators/create_lighting_setup.py#L59):

```python
if hasattr(context.scene.cycles, 'feature_set'):
    context.scene.cycles.feature_set = 'EXPERIMENTAL'
```

This is the only place in the codebase that references `feature_set`.

## Implementation Steps

1. Edit [create_lighting_setup.py](MakeTile/operators/create_lighting_setup.py) line 59.
2. Wrap the assignment in `hasattr`.
3. Run `python -m py_compile` on the file.
4. Re-test **Create Lighting Setup** in Blender 5.

## Success Criteria

- No `AttributeError` when switching to Cycles view mode in Blender 5.
- Blender 4.x still sets the experimental feature set when available.

## Risk Assessment

- **Very low risk.** One-line guard; no functional change on supported Blender versions.

## Next Steps

- Implement the guard and re-test.
