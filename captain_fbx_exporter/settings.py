import bpy


class CAPTAINEXPORT_Settings(bpy.types.PropertyGroup):
    export_dir: bpy.props.StringProperty(
        name="Папка экспорта",
        description="Folder used for exported FBX files",
        subtype='DIR_PATH',
        default="D:/Dev/Blender/Captain/"
    )
    model_name: bpy.props.StringProperty(
        name="Имя модели",
        description="FBX filename for the character model",
        default="Captain_Model.fbx"
    )
    export_all: bpy.props.BoolProperty(
        name="Экспорт всех анимаций",
        description="Export every Action as a separate FBX file",
        default=False
    )
    debug_dump: bpy.props.BoolProperty(
        name="Сохранять дамп иерархии",
        description="Write a text hierarchy dump beside each animation FBX",
        default=False
    )


def register():
    bpy.utils.register_class(CAPTAINEXPORT_Settings)
    bpy.types.Scene.captain_export_settings = bpy.props.PointerProperty(type=CAPTAINEXPORT_Settings)


def unregister():
    del bpy.types.Scene.captain_export_settings
    bpy.utils.unregister_class(CAPTAINEXPORT_Settings)
