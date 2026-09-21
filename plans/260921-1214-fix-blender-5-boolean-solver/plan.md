# Fix Plan: Blender 5 boolean solver enum error

## Context

Issue [#2](https://github.com/ChuChuCharlie/make-tile/issues/2) reports a `TypeError` when creating a new tile in Blender 5:

```
TypeError: bpy_struct: item.attr = val: enum "FAST" not found in ('FLOAT', 'EXACT', 'MANIFOLD')
```

The traceback points to `MakeTile/tile_creation/create_tile.py:1027`, where `boolean.solver = solver` is assigned the value `"FAST"`.

## Root Cause

Blender renamed the fast boolean solver identifier from `'FAST'` to `'FLOAT'` in Blender 5.0. The enum values are:

- Blender 4.5: `['FAST', 'EXACT', 'MANIFOLD']` — [API docs](https://docs.blender.org/api/4.5/bpy.types.BooleanModifier.html)
- Blender 5.0/5.2: `['FLOAT', 'EXACT', 'MANIFOLD']` — [API docs](https://docs.blender.org/api/5.0/bpy.types.BooleanModifier.html)

MakeTile hard-codes `solver='FAST'` in `set_bool_props()` and in several callers. This fails on Blender 5 because the identifier no longer exists.

## Scope

- Primary fix: `MakeTile/tile_creation/create_tile.py` — `set_bool_props()`.
- Callers pass `solver='FAST'` or `solver='EXACT'`. `EXACT` is unchanged across versions, so only `FAST` needs mapping.
- `MakeTile/tile_creation/Mini_Bases.py:804` assigns `bool.solver = "EXACT"` directly and does not need changes.

## Proposed Fix

Add a small helper inside `create_tile.py` that resolves a requested solver to a valid identifier at runtime:

```python
def resolve_boolean_solver(requested='FAST'):
    """Return a boolean solver identifier valid in the current Blender version.

    Blender 5.0 renamed 'FAST' to 'FLOAT'. 'EXACT' and 'MANIFOLD' are unchanged.
    """
    items = bpy.types.BooleanModifier.bl_rna.properties['solver'].enum_items
    identifiers = {item.identifier for item in items}

    if requested in identifiers:
        return requested

    # Cross-version mapping for the renamed fast/Float solver.
    mapped = {'FAST': 'FLOAT', 'FLOAT': 'FAST'}.get(requested)
    if mapped and mapped in identifiers:
        return mapped

    # Safe fallback order.
    for choice in ('EXACT', 'FLOAT', 'FAST', 'MANIFOLD'):
        if choice in identifiers:
            return choice

    return 'EXACT'
```

Then change `set_bool_props()` to use it:

```python
def set_bool_props(bool_obj, target_obj, bool_type, solver='FAST'):
    ...
    boolean.solver = resolve_boolean_solver(solver)
    ...
```

This preserves the existing intent (fast solver) on Blender 4.x and maps it to `FLOAT` on Blender 5.x.

## Implementation Steps

1. Open `MakeTile/tile_creation/create_tile.py`.
2. Add `resolve_boolean_solver()` near `set_bool_props()`.
3. Update `set_bool_props()` to call `resolve_boolean_solver(solver)` before assigning `boolean.solver`.
4. Update the `set_bool_props()` docstring to reflect that `solver` is resolved at runtime and may be `'FAST'` or `'EXACT'`.
5. Run the existing smoke test (`test_addon_blender.py`) or a quick in-Blender import check to confirm no syntax errors.
6. (Optional) Have a tester create a Straight Wall and an L Tile in Blender 5 to verify the tile creation path no longer raises the enum error.

## Success Criteria

- `set_bool_props()` no longer raises `TypeError` when `solver='FAST'` is requested in Blender 5.
- The add-on continues to work in Blender 4.x (backward compatibility).
- No other boolean-related solver assignments are broken.

## Risk Assessment

- **Low risk.** The fix is localized to a single helper. `EXACT` callers are unaffected.
- **Blender 3.2 note:** The project previously targeted Blender 3.2+. The runtime enum check is safer than a version-number `if`, because it adapts to whichever identifiers the current Blender build exposes.

## Next Steps

- Implement the fix in `create_tile.py`.
- Run tests and, if passing, request code review.
