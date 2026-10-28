import bpy


class CAPTAINEXPORT_PT_panel(bpy.types.Panel):
    bl_label = "Captain Export"
    bl_idname = "CAPTAINEXPORT_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Captain Export"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.captain_export_settings

        layout.prop(settings, "export_dir")
        layout.separator()
        layout.label(text="Модель")
        layout.prop(settings, "model_name")
        layout.operator("captain_export.model", icon='EXPORT')
        layout.separator()
        layout.label(text="Анимации")
        layout.prop(settings, "export_all")
        layout.prop(settings, "debug_dump")
        layout.operator("captain_export.animations", icon='ACTION')


def register():
    bpy.utils.register_class(CAPTAINEXPORT_PT_panel)


def unregister():
    bpy.utils.unregister_class(CAPTAINEXPORT_PT_panel)
