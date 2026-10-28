import bpy
import os

from .common import get_armature, get_filepath_name, save_selection, restore_selection, log_hierarchy


class CAPTAINEXPORT_OT_animations(bpy.types.Operator):
    bl_idname = "captain_export.animations"
    bl_label = "Экспорт анимаций"
    bl_description = "Export the current Action or all Actions as separate FBX files"

    def execute(self, context):
        settings = context.scene.captain_export_settings
        armature = get_armature(context)

        if not armature:
            self.report({'ERROR'}, "Select the character Armature as the active object")
            return {'CANCELLED'}
        if not settings.export_dir:
            self.report({'ERROR'}, "Specify the export folder")
            return {'CANCELLED'}

        original_action = armature.animation_data.action if armature.animation_data else None
        actions = list(bpy.data.actions) if settings.export_all else ([original_action] if original_action else [])
        if not actions:
            self.report({'ERROR'}, "No Action selected and no Actions to export")
            return {'CANCELLED'}

        scene = context.scene
        original_scene_name = scene.name
        original_parent = armature.parent
        original_world = armature.matrix_world.copy()
        original_parent_inverse = armature.matrix_parent_inverse.copy()
        original_basis = armature.matrix_basis.copy()
        original_frame_start = scene.frame_start
        original_frame_end = scene.frame_end
        original_frame_current = scene.frame_current
        original_selection = save_selection(context)
        original_anim_data_exists = armature.animation_data is not None
        original_root = None
        exported = 0
        errors = []
        export_dir = bpy.path.abspath(settings.export_dir)

        try:
            os.makedirs(export_dir, exist_ok=True)
            original_root = bpy.data.objects.new("AnimationRoot", None)
            original_root.empty_display_type = 'PLAIN_AXES'
            original_root.empty_display_size = 0.25
            collection = armature.users_collection[0] if armature.users_collection else scene.collection
            collection.objects.link(original_root)

            armature.parent = original_root
            armature.matrix_world = original_world
            context.view_layer.update()

            if not armature.animation_data:
                armature.animation_data_create()

            for action in actions:
                if not action:
                    continue
                try:
                    scene.name = get_filepath_name(action.name)
                    armature.animation_data.action = action
                    scene.frame_start = int(action.frame_range[0])
                    scene.frame_end = int(action.frame_range[1])
                    scene.frame_set(scene.frame_start)

                    bpy.ops.object.select_all(action='DESELECT')
                    original_root.select_set(True)
                    armature.select_set(True)
                    context.view_layer.objects.active = armature

                    filepath = os.path.join(export_dir, get_filepath_name(action.name) + ".fbx")
                    if settings.debug_dump:
                        debug_path = os.path.join(export_dir, get_filepath_name(action.name) + "_blender.txt")
                        log_hierarchy(context, armature, action, debug_path)

                    bpy.ops.export_scene.fbx(
                        filepath=filepath,
                        use_selection=True,
                        object_types={'EMPTY', 'ARMATURE'},
                        bake_anim=True,
                        bake_anim_use_nla_strips=False,
                        bake_anim_use_all_actions=False,
                        add_leaf_bones=False,
                        armature_nodetype='NULL',
                        apply_scale_options='FBX_SCALE_UNITS',
                        bake_anim_force_startend_keying=True
                    )
                    exported += 1
                except Exception as exc:
                    errors.append(f"{action.name}: {exc}")
        finally:
            armature.parent = original_parent
            armature.matrix_parent_inverse = original_parent_inverse
            armature.matrix_basis = original_basis
            armature.matrix_world = original_world

            if original_anim_data_exists:
                armature.animation_data.action = original_action
            elif armature.animation_data:
                armature.animation_data_clear()

            scene.frame_start = original_frame_start
            scene.frame_end = original_frame_end
            scene.frame_set(original_frame_current)
            scene.name = original_scene_name

            if original_root:
                bpy.data.objects.remove(original_root, do_unlink=True)

            restore_selection(context, original_selection)

        if errors:
            self.report({'WARNING'}, f"Exported {exported}; failed: {'; '.join(errors[:3])}")
        elif exported:
            self.report({'INFO'}, f"Exported {exported} animation(s)")
        else:
            self.report({'ERROR'}, "No animations were exported")
            return {'CANCELLED'}

        return {'FINISHED'}


def register():
    bpy.utils.register_class(CAPTAINEXPORT_OT_animations)


def unregister():
    bpy.utils.unregister_class(CAPTAINEXPORT_OT_animations)
