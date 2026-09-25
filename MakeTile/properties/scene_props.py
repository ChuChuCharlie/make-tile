import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    EnumProperty,
    BoolProperty,
    FloatProperty,
    IntProperty,
    PointerProperty)
from ..enums.enums import (
    units,
    material_mapping)
from ..tile_creation.create_tile import MT_Tile_Generator
from ..lib.utils.utils import get_all_subclasses, get_annotations
from ..tile_creation.create_tile import create_tile_type_enums
from ..app_handlers import load_tile_defaults

def update_disp_strength(self, context):
    """Update the displacement strength of the maketile displacement modifier on active object.

    Args:
        context (bpy.context): context
    """
    obj = bpy.context.active_object
    if context.active_object.select_get():
        obj_props = obj.mt_object_props
        obj_props.displacement_strength = context.scene.mt_scene_props.displacement_strength
        try:
            obj.modifiers[obj_props.disp_mod_name].strength = context.scene.mt_scene_props.displacement_strength
        except KeyError:
            pass


def update_disp_subdivisions(self, context):
    """Update the number of subdivisions used by the displacement material modifier."""

    selected = [ob for ob in context.selected_editable_objects if ob.mt_object_props.is_displacement]
    for obj in selected:
        obj_props = obj.mt_object_props
        try:
            obj.modifiers[obj_props.subsurf_mod_name].levels = context.scene.mt_scene_props.subdivisions
        except KeyError:
            pass


def update_material_mapping(self, context):
    '''updates which mapping method to use for a material'''
    material = context.object.active_material
    tree = material.node_tree
    nodes = tree.nodes

    map_meth = context.scene.mt_scene_props.material_mapping_method

    if 'master_mapping' in nodes:
        mapping_node = nodes['master_mapping']
        if map_meth == 'WRAP_AROUND':
            map_type_node = nodes['wrap_around_map']
            tree.links.new(
                map_type_node.outputs['Vector'],
                mapping_node.inputs['Vector'])
        elif map_meth == 'TRIPLANAR':
            map_type_node = nodes['triplanar_map']
            tree.links.new(
                map_type_node.outputs['Vector'],
                mapping_node.inputs['Vector'])
        elif map_meth == 'OBJECT':
            map_type_node = nodes['object_map']
            tree.links.new(
                map_type_node.outputs['Color'],
                mapping_node.inputs['Vector'])
        elif map_meth == 'GENERATED':
            map_type_node = nodes['generated_map']
            tree.links.new(
                map_type_node.outputs['Color'],
                mapping_node.inputs['Vector'])
        elif map_meth == 'UV':
            map_type_node = nodes['UV_map']
            tree.links.new(
                map_type_node.outputs['Color'],
                mapping_node.inputs['Vector'])


def reset_part_defaults(self, context):
    tile_type = self.tile_type
    base_blueprint = self.base_blueprint
    main_part_blueprint = self.main_part_blueprint
    tile_defaults = load_tile_defaults(context)
    for tile in tile_defaults:
        if tile['type'] == tile_type:
            defaults = tile['defaults']
            base_defaults = defaults['base_defaults']
            for key, value in base_defaults.items():
                if key == base_blueprint:
                    for k, v in value.items():
                        setattr(self, k, v)
                    break
            try:
                main_part_defaults = defaults['tile_defaults']
                for key, value in main_part_defaults.items():
                    if key == main_part_blueprint:
                        for k, v in value.items():
                            setattr(self, k, v)
                        break
            # Some tiles like mini bases don;t have main parts
            except KeyError:
                pass
            break


def _apply_tile_type_defaults():
    """Apply defaults for the current tile_type and redraw the UI.

    This is run as a deferred timer callback so that the EnumProperty dropdown
    UI can finish updating before we touch dependent properties such as
    ``base_blueprint`` and ``main_part_blueprint``.
    """
    context = bpy.context
    scene = context.scene
    if not hasattr(scene, 'mt_scene_props'):
        return None

    scene_props = scene.mt_scene_props
    tile_type = scene_props.tile_type
    tile_defaults = load_tile_defaults(context)
    tile_def = None
    for tile in tile_defaults:
        if tile['type'] == tile_type:
            tile_def = tile
            break

    if tile_def is None:
        print(
            f"MakeTile warning: no defaults found for tile type {tile_type}")
        return None

    defaults = tile_def['defaults']
    valid_base_blueprints = set(tile_def.get('base_blueprints', {}).keys())
    valid_main_part_blueprints = set(
        tile_def.get('main_part_blueprints', {}).keys())

    new_base_blueprint = defaults.get('base_blueprint')
    if new_base_blueprint not in valid_base_blueprints and valid_base_blueprints:
        new_base_blueprint = next(iter(sorted(valid_base_blueprints)))

    new_main_part_blueprint = defaults.get('main_part_blueprint')
    if new_main_part_blueprint not in valid_main_part_blueprints and valid_main_part_blueprints:
        new_main_part_blueprint = next(iter(sorted(valid_main_part_blueprints)))

    if new_base_blueprint is not None and hasattr(scene_props, 'base_blueprint'):
        setattr(scene_props, 'base_blueprint', new_base_blueprint)
    if new_main_part_blueprint is not None and hasattr(scene_props, 'main_part_blueprint'):
        setattr(scene_props, 'main_part_blueprint', new_main_part_blueprint)

    for key, value in defaults.items():
        if key in ('base_blueprint', 'main_part_blueprint'):
            continue
        if hasattr(scene_props, key):
            try:
                setattr(scene_props, key, value)
            except TypeError:
                pass

    reset_part_defaults(scene_props, context)

    # Force a full UI redraw so panels update on the first dropdown click.
    try:
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
    except Exception:
        pass

    # Clear the deferral flag so future tile_type changes queue a new timer.
    if '_mt_deferring_tile_type_update' in scene_props:
        del scene_props['_mt_deferring_tile_type_update']

    return None


def update_scene_defaults(self, context):
    """Update scene properties when the tile type changes.

    Instead of applying defaults immediately inside the EnumProperty update
    callback, we register a one-shot timer. This lets Blender finish updating
    the dropdown UI first, which fixes the issue where the first selection
    appeared not to apply until a second click.
    """
    if self.get('_mt_deferring_tile_type_update', False):
        return

    self['_mt_deferring_tile_type_update'] = True
    try:
        bpy.app.timers.register(
            _apply_tile_type_defaults,
            first_interval=0.01,
            persistent=False)
    except Exception as err:
        print(f"MakeTile warning: failed to defer tile type update: {err}")
        # Fall back to immediate application if the timer cannot be registered.
        _apply_tile_type_defaults()
    finally:
        # The flag is cleared by the timer; leave it set here so repeated
        # rapid changes don't queue multiple timers.
        pass


def create_scene_props():
    """Dynamically create MT_Scene_Props property group.
    """

    # Manually created properties for exporter etc.
    props = {
        "displacement_strength": FloatProperty(
            name="Displacement Strength",
            description="Overall Displacement Strength",
            default=0.1,
            step=1,
            precision=3,
            update=update_disp_strength),
        "mt_last_selected": PointerProperty(
            name="Last Selected Object",
            type=bpy.types.Object),
        "material_mapping_method": EnumProperty(
            items=material_mapping,
            description="How to map the active material onto an object",
            name="Material Mapping Method",
            update=update_material_mapping,
            default='OBJECT'),
        "base_unit": EnumProperty(
            name="Base Unit",
            items=units),
        "target_unit": EnumProperty(
            name="Target Unit",
            items=units),
        "tile_resolution": IntProperty(
            name="Resolution",
            description="Bake resolution of displacement maps. Higher = better quality but slower. Also images are 32 bit so 4K and 8K images can be gigabytes in size",
            default=1024,
            min=1024,
            max=8192,
            step=1024),
        "voxel_size": FloatProperty(
            name="Voxel Size",
            description="Quality of the voxelisation. Smaller = Better",
            soft_min=0.005,
            default=0.0051,
            precision=3),
        "voxel_adaptivity": FloatProperty(
            name="Adaptivity",
            description="Amount by which to simplify mesh",
            default=0.25,
            precision=3),
        "voxel_merge": BoolProperty(
            name="Merge",
            description="Merge objects on voxelisation? Creates a single mesh.",
            default=True),
        "fix_non_manifold": BoolProperty(
            name="Fix non-manifold",
            description="Attempt to fix geometry errors",
            default=True),
        "decimation_ratio": FloatProperty(
            name="Decimation Ratio",
            description="Amount to decimate by. Smaller = more simplification",
            min=0.0,
            max=1,
            precision=3,
            step=0.01,
            default=0.25),
        "decimation_merge": BoolProperty(
            name="Merge",
            description="Merge selected before decimation",
            default=True),
        "planar_decimation": BoolProperty(
            name="Planar Decimation",
            description="Further simplify the planar (flat) parts of the mesh",
            default=False),
        "planar_decimation_angle": FloatProperty(
            name="Decimation Angle",
            description="Angle below which to simplify",
            default=5,
            max=90,
            min=0,
            step=5),
        "num_variants": IntProperty(
            name="Variants",
            description="Number of variants of tile to export",
            default=1),
        "randomise_on_export": BoolProperty(
            name="Randomise",
            description="Create random variant on export?",
            default=True),
        "voxelise_on_export": BoolProperty(
            name="Voxelise",
            default=True),
        "decimate_on_export": BoolProperty(
            name="Decimate",
            default=False),
        "export_units": EnumProperty(
            name="Units",
            items=units,
            description="Export units",
            default='INCHES'),
        "subdivisions": IntProperty(
            name="Subdivisions",
            description="How many times to subdivide the displacement mesh with a subsurf modifier. Higher = better but slower.",
            default=3,
            soft_max=8,
            update=update_disp_subdivisions),
        # rather than creating this in the the MT_Tile_Generator class and copying it we set it seperately here
        # and in the tile_props to allow us to have different update functions
        "tile_type": EnumProperty(
            items=create_tile_type_enums,
            name="Tile Type",
            update=update_scene_defaults,
            description="The type of tile e.g. Straight Wall, Curved Floor"
        ),
        "is_scene_props": BoolProperty(
            default=True)
    }

    # dynamically created properties constructed from all annotations in subclasses of MT_Tile_Generator
    subclasses = get_all_subclasses(MT_Tile_Generator)
    annotations = {}

    for subclass in subclasses:
        # make sure we also get annotations of parent classes such as mixins
        annotations.update(get_annotations(subclass))
        annotations.update(subclass.__annotations__)
        annotations.update(props)

    # exclusion list
    exclude = ["invoked", "executed"]
    for item in exclude:
        del annotations[item]

    MT_Scene_Props = type(
        'New_MT_Scene_Props',
        (PropertyGroup,),
        {'__annotations__': annotations})
    bpy.utils.register_class(MT_Scene_Props)
    PointerSceneProps = PointerProperty(type=MT_Scene_Props)
    setattr(bpy.types.Scene, "mt_scene_props", PointerSceneProps)

def register():
    try:
        create_scene_props()
    except Exception as err:
        print(f"MakeTile error: failed to create scene properties: {err}")
        import traceback
        traceback.print_exc()
        raise

def unregister():
    try:
        del bpy.types.Scene.mt_scene_props
    except AttributeError:
        pass
