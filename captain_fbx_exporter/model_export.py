import bpy
import os

from .common import get_armature, get_export_objects, get_filepath_name, save_selection, restore_selection


class CAPTAINEXPORT_OT_model(bpy.types.Operator):
    bl_idname = "captain_export.model"
    bl_label = "Экспорт модели"
    bl_description = "Export the selected character model without animation"

    def execute(self, context):
        settings = context.scene.captain_export_settings
        armature = get_armature(context)

        if not armature:
            self.report({'ERROR'}, "Select the character Armature as the active object")
            return {'CANCELLED'}
        if not settings.export_dir:
            self.report({'ERROR'}, "Specify the export folder")
            return {'CANCELLED'}

        export_objects = get_export_objects(context, armature)
        state = save_selection(context)
        export_dir = bpy.path.abspath(settings.export_dir)
        filepath = os.path.join(export_dir, get_filepath_name(settings.model_name))
        if not filepath.lower().endswith(".fbx"):
            filepath += ".fbx"

        try:
            os.makedirs(export_dir, exist_ok=True)
            bpy.ops.object.select_all(action='DESELECT')
            for obj in export_objects:
                obj.select_set(True)
            context.view_layer.objects.active = armature

            bpy.ops.export_scene.fbx(
                filepath=filepath,
                use_selection=True,
                object_types={'ARMATURE', 'MESH'},
                use_mesh_modifiers=True,
                add_leaf_bones=False,
                armature_nodetype='NULL',
                bake_anim=False,
                apply_scale_options='FBX_SCALE_UNITS',
                path_mode='AUTO'
            )
        except Exception as exc:
            self.report({'ERROR'}, f"Model export failed: {exc}")
            return {'CANCELLED'}
        finally:
            restore_selection(context, state)

        self.report({'INFO'}, f"Model exported: {filepath}")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(CAPTAINEXPORT_OT_model)


def unregister():
    bpy.utils.unregister_class(CAPTAINEXPORT_OT_model)
