import bpy
import re


def get_armature(context):
    obj = context.active_object
    return obj if obj and obj.type == 'ARMATURE' else None


def get_export_objects(context, armature):
    view_objects = set(context.view_layer.objects)
    objects = {armature}
    objects.update(
        obj for obj in armature.children_recursive
        if obj.type == 'MESH' and obj in view_objects
    )
    return objects


def get_filepath_name(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip() or "Animation"


def save_selection(context):
    return list(context.selected_objects), context.view_layer.objects.active


def restore_selection(context, state):
    selected, active = state
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selected:
        if obj.name in context.view_layer.objects:
            obj.select_set(True)
    if active and active.name in context.view_layer.objects:
        context.view_layer.objects.active = active


def log_hierarchy(context, armature, action, filepath):
    lines = [
        f"ACTION: {action.name}",
        f"ARMATURE: {armature.name}",
        f"ARMATURE TYPE: {armature.type}",
        "OBJECT HIERARCHY:",
    ]

    def log_object(obj, depth=0):
        indent = "  " * depth
        loc = tuple(round(v, 5) for v in obj.location)
        rot = tuple(round(v, 5) for v in obj.rotation_euler)
        scale = tuple(round(v, 5) for v in obj.scale)
        parent = obj.parent.name if obj.parent else "None"
        lines.append(
            f"{indent}{obj.name} [{obj.type}] "
            f"parent={parent} loc={loc} rot={rot} scale={scale}"
        )
        for child in sorted(obj.children, key=lambda o: o.name):
            log_object(child, depth + 1)

    for obj in context.scene.objects:
        if obj.parent is None:
            log_object(obj)

    lines.extend(["", "BONE HIERARCHY:"])

    def log_bone(bone, depth=0):
        lines.append("  " * depth + bone.name)
        for child in sorted(bone.children, key=lambda b: b.name):
            log_bone(child, depth + 1)

    for bone in armature.data.bones:
        if bone.parent is None:
            log_bone(bone)

    with open(filepath, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
