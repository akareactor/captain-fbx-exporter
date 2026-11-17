bl_info = {
    "name": "Captain FBX Exporter",
    "author": "KulibinSpace",
    "version": (1, 2, 0),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > Captain Export",
    "description": "Export character models and animation clips to FBX",
    "category": "Import-Export",
}

from . import settings, model_export, animation_export, collection_export, ui


def register():
    settings.register()
    model_export.register()
    animation_export.register()
    collection_export.register()
    ui.register()


def unregister():
    ui.unregister()
    collection_export.unregister()
    animation_export.unregister()
    model_export.unregister()
    settings.unregister()
