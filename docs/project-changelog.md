# Project Changelog

All notable changes to MakeTile are documented in this file.

## [Unreleased]

### Fixed

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
