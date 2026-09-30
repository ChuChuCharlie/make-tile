# Project Changelog

All notable changes to MakeTile are documented in this file.

## [Unreleased]

### Fixed

- **Issue #29** — Fixed `spawn_openlock_base_clip_cutters` in [`MakeTile/tile_creation/Triangular_Tiles.py`](../../MakeTile/tile_creation/Triangular_Tiles.py) so triangular floor tiles no longer raise `TypeError: 'NoneType' object is not iterable` for short legs.
  - The function now always returns a list (empty when no cutters are needed).
  - OpenLOCK clip cutters are only added to Leg 1 / Leg 2 when the leg is at least 2.0; shorter legs leave no room and cause the boolean difference to clip through adjacent geometry.
  - The bottom slot cutter is only added when both legs are at least 1.5; otherwise it clips through adjacent geometry.
  - The hypotenuse cutter is still added for isosceles right triangles when the hypotenuse is longer than 1.5.
  - Added regression tests in [`tests/test_triangular_floor.py`](../../tests/test_triangular_floor.py) covering the reported dimension matrix and asymmetric cases up to 5×1 at 90° and 60°.
  - Severity: high. Impact: restores triangular floor tile generation for small OpenLOCK bases.
  - When one leg is `<= 1.5` and the other leg is `>= 2.0`, the short leg gets no cutter and the long leg is capped at `floor(leg) - 1` total cutters (1 for 2.x, 2 for 3.x, 3 for 4.x, ...). Leg 1 recomputes `fit_length` to produce exactly that count. Leg 2 repositions the strip so it does not shift past the short-leg corner / hypotenuse.
  - Added `min=0.5` / `soft_min=0.5` to `leg_1_len` and `leg_2_len`, and `min=1` / `max=179` / `soft_min=1` / `soft_max=179` to `angle`, to prevent invalid triangle dimensions in the UI.
  - Added `update` callbacks and runtime clamping in `MT_OT_Make_Triangular_Floor_Tile.execute` so values below the minimum are clamped before generation even when the UI field accepts a typed value.
  - Added shared `leg_1_len`, `leg_2_len`, and `angle` definitions with limits to `MT_Scene_Props` in [`MakeTile/properties/scene_props.py`](../../MakeTile/properties/scene_props.py), so the Triangular Floor sidebar panel enforces the same minimums even when other tile subclasses define the same property names without limits.

- **U-Wall creation fails on Blender 4.4+** — Updated `MT_Tile_Generator.__init__` in [`MakeTile/tile_creation/create_tile.py`](../../MakeTile/tile_creation/create_tile.py) to accept and forward internal constructor arguments (`*args, **kwargs`) to the base `bpy.types.Operator` class.
  - Blender 4.4 changed operator instantiation so that subclasses must forward opaque internal arguments from `__init__`; the previous `def __init__(self):` signature raised `TypeError: MT_Tile_Generator.__init__() takes 1 positional argument but 2 were given` when creating any tile derived from `MT_Tile_Generator`, including U-Walls.
  - Added regression tests in [`tests/test_u_tiles.py`](../../tests/test_u_tiles.py) covering the main U-Wall blueprint combinations.
  - Severity: high. Impact: restores tile generation on Blender 4.4 and 5.x.

- **Issue #23** — Replaced expensive `bm_shortest_path` calls in [`MakeTile/tile_creation/U_Tiles.py`](../../MakeTile/tile_creation/U_Tiles.py) with Z-plane + X/Y bounds selection when building U-Wall bottom vertex groups.
  - The bottom ring of a U core is coplanar and its Z is controlled by the same creation path (`base_height` for `SIDE`/`CENTER`, `0.0` for `EXTERIOR`), so a thin Z slice plus the existing `select_verts_in_bounds` helper selects the same vertices as the previous per-pair Dijkstra searches.
  - Removed the `bm_shortest_path` import from `U_Tiles.py`; the helper is still available in [`MakeTile/lib/bmturtle/helpers.py`](../../MakeTile/lib/bmturtle/helpers.py) for other tiles.
  - Added regression tests that verify bottom/top vertex groups exist and that `bm_shortest_path` is no longer called during U-Wall generation.
  - Severity: medium. Impact: faster U-Wall generation, especially at high subdivision density.

- **Issue #19** — Reduced mode switching in the object converter ([`MakeTile/operators/object_converter.py`](../../MakeTile/operators/object_converter.py)).
  - Avoid the `bpy.ops.object.vertex_group_move` loop entirely when the source mesh has no pre-existing vertex groups; create `"All"` first so it naturally occupies index 0.
  - Keep the move loop only when pre-existing groups exist, but run it in object mode (no edit/object churn).
  - Wrap the remaining single edit-mode switch required by `bpy.ops.uv.smart_project` in `try/finally`.
  - Add tests verifying `"All"` ends up at index 0 and that existing groups are used for material assignment.
  - Severity: low. Impact: faster and more reliable conversion, especially for meshes with many vertex groups.
