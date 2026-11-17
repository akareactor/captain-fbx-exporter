# Collection hierarchy export for Captain FBX Exporter. "location": "Outliner > Collection > Right Click",
# Registered via captain_exporter/__init__.py; no bl_info here on purpose.

import bpy
import os
import traceback
from mathutils import Matrix


# ------------------------------------------------------------------------
# Export preparation
# ------------------------------------------------------------------------

class ExportBuilder:
    def __init__(self, context, temp_scene):
        self.context = context
        self.temp_scene = temp_scene
        self.depsgraph = context.evaluated_depsgraph_get()
        self.mesh_cache = {}
        self.created_objects = []
        self.created_meshes = []
        self.object_records = []
        self.collection_stack = []
        self.instance_count = 0
        self.mesh_object_count = 0
        self.warnings = []
        # Pointers of collections that were expanded as instances. Used to
        # avoid re-expanding the same collection if it also happens to be a
        # child of the exported collection.
        self.instanced_collections = set()
        # Unique object names used in the export scene, to avoid Blender's
        # automatic ".001" suffixes and keep names readable in Unity.
        self.used_names = set()

    def link_object(self, obj):
        self.temp_scene.collection.objects.link(obj)
        self.created_objects.append(obj)
        return obj

    def unique_name(self, base):
        name = base
        if name in self.used_names:
            suffix = 1
            while f"{base}_{suffix}" in self.used_names:
                suffix += 1
            name = f"{base}_{suffix}"
        self.used_names.add(name)
        return name

    def create_empty(self, name, parent=None, world_matrix=None, size=0.25):
        obj = bpy.data.objects.new(self.unique_name(name), None)
        obj.empty_display_type = 'PLAIN_AXES'
        obj.empty_display_size = size
        self.link_object(obj)
        if parent:
            obj.parent = parent
        obj.matrix_world = world_matrix.copy() if world_matrix else Matrix.Identity(4)
        return obj

    def mesh_cache_key(self, source_obj):
        # Unmodified mesh datablocks can always share their evaluated geometry.
        # Modified objects share only with instances of that exact source object.
        if source_obj.type == 'MESH' and len(source_obj.modifiers) == 0:
            return ("MESH_DATA", source_obj.data.as_pointer())
        return ("SOURCE_OBJECT", source_obj.as_pointer())

    def get_mesh(self, source_obj):
        key = self.mesh_cache_key(source_obj)
        if key in self.mesh_cache:
            return self.mesh_cache[key]

        evaluated_obj = source_obj.evaluated_get(self.depsgraph)
        mesh = bpy.data.meshes.new_from_object(
            evaluated_obj,
            preserve_all_data_layers=True,
            depsgraph=self.depsgraph
        )
        if mesh is None:
            return None

        mesh.name = f"{source_obj.name}_ExportMesh"
        self.mesh_cache[key] = mesh
        self.created_meshes.append(mesh)
        return mesh

    def add_source_object(self, source_obj, parent_empty, base_matrix, scope_id):
        world_matrix = base_matrix @ source_obj.matrix_world
        if source_obj.type in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}:
            mesh = self.get_mesh(source_obj)
            if mesh is None:
                self.warnings.append(f"Could not evaluate geometry: {source_obj.name}")
                return None
            new_obj = bpy.data.objects.new(
                self.unique_name(source_obj.name), mesh
            )
            self.mesh_object_count += 1
        elif source_obj.type == 'EMPTY':
            new_obj = bpy.data.objects.new(self.unique_name(source_obj.name), None)
            new_obj.empty_display_type = 'PLAIN_AXES'
            new_obj.empty_display_size = 0.15
        else:
            # Non-geometric scene objects are not part of a static Unity model.
            return None

        self.link_object(new_obj)
        new_obj.parent = parent_empty
        new_obj.matrix_world = world_matrix.copy()
        self.object_records.append({
            "source": source_obj,
            "target": new_obj,
            "scope": scope_id,
            "world": world_matrix.copy(),
            "fallback_parent": parent_empty,
        })
        return new_obj

    def add_manual_instancer(self, source_obj, parent_empty, base_matrix,
                             scope_id, recursion_stack):
        """
        Expand a modifier-free collection instancer by walking the instance
        collection directly. Meshes are deduplicated via mesh_cache, so N
        references to the same source mesh produce N objects sharing one
        bpy.data.meshes datablock -> one Geometry node in FBX.
        """
        instancer_world = base_matrix @ source_obj.matrix_world
        instancer_empty = self.create_empty(
            source_obj.name, parent_empty, instancer_world, 0.2
        )
        self.object_records.append({
            "source": source_obj,
            "target": instancer_empty,
            "scope": scope_id,
            "world": instancer_world.copy(),
            "fallback_parent": parent_empty,
        })

        instance_collection = source_obj.instance_collection
        offset_matrix = Matrix.Translation(-instance_collection.instance_offset)
        instance_base = instancer_world @ offset_matrix
        self.instance_count += 1
        self.instanced_collections.add(instance_collection.as_pointer())

        child_scope = object()
        self.process_collection(
            instance_collection,
            instancer_empty,
            instance_base,
            child_scope,
            recursion_stack,
            node_name=instance_collection.name
        )
        return instancer_empty

    def add_baked_instancer(self, source_obj, parent_empty, base_matrix, scope_id):
        """
        Handle a collection instancer that carries modifiers (Array, Mirror,
        etc.). The depsgraph has already evaluated the modifier result into N
        object_instances; we materialize each as a real MESH object, but share
        the mesh datablock between instances whose evaluated mesh pointer is
        identical.

        Sharing is what makes FBX deduplicate geometry: N objects referencing
        one bpy.data.meshes datablock -> one Geometry node + N Model nodes in
        FBX -> one Mesh asset + N GameObjects in Unity.

        Object names are taken from the original source object (tube, fitting,
        ...) with a numeric suffix only on collision, so Unity shows the
        original detail names instead of "Spaceframe3_0", "Spaceframe3_1", ...

        Note: modifiers that change topology per-copy (e.g. Array with merge,
        Boolean, Remesh) will produce a distinct evaluated mesh per instance.
        Those correctly become separate meshes; there is nothing to share.
        """
        depsgraph = self.depsgraph
        evaluated_obj = source_obj.evaluated_get(depsgraph)
        instancer_world = base_matrix @ source_obj.matrix_world

        # Keep the instancer as an EMPTY so the transform hierarchy survives
        # even if the modifier produces no geometry at all.
        instancer_empty = self.create_empty(
            source_obj.name, parent_empty, instancer_world, 0.2
        )
        self.object_records.append({
            "source": source_obj,
            "target": instancer_empty,
            "scope": scope_id,
            "world": instancer_world.copy(),
            "fallback_parent": parent_empty,
        })

        self.instance_count += 1
        self.instanced_collections.add(source_obj.instance_collection.as_pointer())

        created = 0
        for inst in depsgraph.object_instances:
            if inst.parent != evaluated_obj:
                continue
            inst_obj = inst.object
            if inst_obj.type != 'MESH':
                continue

            key = ("BAKED", inst_obj.data.as_pointer())
            mesh = self.mesh_cache.get(key)
            if mesh is None:
                mesh = bpy.data.meshes.new_from_object(
                    inst_obj,
                    preserve_all_data_layers=True,
                    depsgraph=depsgraph
                )
                if mesh is None:
                    continue
                mesh.name = f"{source_obj.name}_BakedMesh"
                self.mesh_cache[key] = mesh
                self.created_meshes.append(mesh)

            # Use the original object's name (tube, fitting, ...) instead of
            # the instancer's name. Suffix is added only on collision.
            base_name = inst_obj.name
            original = getattr(inst_obj, "original", None)
            if original is not None and getattr(original, "name", None):
                base_name = original.name
            new_obj = bpy.data.objects.new(
                self.unique_name(base_name), mesh
            )
            self.link_object(new_obj)
            new_obj.parent = instancer_empty
            new_obj.matrix_world = base_matrix @ inst.matrix_world
            self.mesh_object_count += 1
            created += 1

        if created == 0:
            self.warnings.append(
                f"Modifier-baked instancer produced no mesh instances: "
                f"{source_obj.name}"
            )
        return instancer_empty

    def process_collection(self, source_collection, parent_empty, base_matrix,
                           scope_id, recursion_stack, node_name=None):
        collection_ptr = source_collection.as_pointer()
        if collection_ptr in recursion_stack:
            self.warnings.append(
                f"Recursive collection instance skipped: {source_collection.name}"
            )
            return None

        recursion_stack = set(recursion_stack)
        recursion_stack.add(collection_ptr)

        collection_empty = self.create_empty(
            node_name or source_collection.name,
            parent_empty,
            base_matrix,
            0.35
        )

        # Create objects in this collection. Collection membership is preserved
        # as hierarchy; object-parent relationships are restored in a second pass.
        for source_obj in source_collection.objects:
            if (source_obj.type == 'EMPTY'
                    and source_obj.instance_type == 'COLLECTION'
                    and source_obj.instance_collection):
                if source_obj.modifiers:
                    self.add_baked_instancer(
                        source_obj, collection_empty, base_matrix, scope_id
                    )
                else:
                    self.add_manual_instancer(
                        source_obj, collection_empty, base_matrix,
                        scope_id, recursion_stack
                    )
            else:
                self.add_source_object(
                    source_obj,
                    collection_empty,
                    base_matrix,
                    scope_id
                )

        # Child collections are organizational hierarchy, not instances.
        # They share the same coordinate space and object-parent scope.
        for child_collection in source_collection.children:
            if child_collection.as_pointer() in self.instanced_collections:
                self.warnings.append(
                    f"Child collection {child_collection.name} already "
                    f"expanded as instance; skipping."
                )
                continue
            self.process_collection(
                child_collection,
                collection_empty,
                base_matrix,
                scope_id,
                recursion_stack
            )

        return collection_empty

    def restore_object_parents(self):
        # Resolve parents only inside the same collection-instance occurrence.
        # This prevents an instance from accidentally parenting to the source
        # object's original, non-instanced occurrence.
        object_map = {}
        for record in self.object_records:
            source = record["source"]
            key = (record["scope"], source.as_pointer())
            object_map[key] = record["target"]

        for record in self.object_records:
            source = record["source"]
            target = record["target"]
            parent = source.parent
            parent_key = (record["scope"], parent.as_pointer()) if parent else None
            new_parent = object_map.get(parent_key) if parent_key else None
            if new_parent and new_parent != target:
                target.parent = new_parent
            else:
                target.parent = record["fallback_parent"]
            target.matrix_world = record["world"]

    def build(self, source_collection):
        root = self.create_empty(
            source_collection.name,
            None,
            Matrix.Identity(4),
            0.5
        )
        root["UnityCollectionExportRoot"] = True
        root_scope = object()
        for source_obj in source_collection.objects:
            if (source_obj.type == 'EMPTY'
                    and source_obj.instance_type == 'COLLECTION'
                    and source_obj.instance_collection):
                if source_obj.modifiers:
                    self.add_baked_instancer(
                        source_obj, root, Matrix.Identity(4), root_scope
                    )
                else:
                    self.add_manual_instancer(
                        source_obj, root, Matrix.Identity(4),
                        root_scope, set()
                    )
            else:
                self.add_source_object(
                    source_obj, root, Matrix.Identity(4), root_scope
                )

        for child_collection in source_collection.children:
            if child_collection.as_pointer() in self.instanced_collections:
                self.warnings.append(
                    f"Child collection {child_collection.name} already "
                    f"expanded as instance; skipping."
                )
                continue
            self.process_collection(
                child_collection,
                root,
                Matrix.Identity(4),
                root_scope,
                set()
            )

        self.restore_object_parents()
        return root


# ------------------------------------------------------------------------
# Operator
# ------------------------------------------------------------------------

class EXPORT_OT_unity_collection_fbx(bpy.types.Operator):
    bl_idname = "captain_export.collection_fbx"
    bl_label = "Export Collection to Unity (.fbx)"
    bl_description = "Export this collection, its children and collection instances to FBX"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default="*.fbx", options={'HIDDEN'})
    collection_name: bpy.props.StringProperty(options={'HIDDEN'})
    axis_forward: bpy.props.EnumProperty(
        name="Forward",
        items=(
            ('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", ""),
            ('-X', "-X", ""), ('-Y', "-Y", ""), ('-Z', "-Z", "")
        ),
        default='Z'
    )
    axis_up: bpy.props.EnumProperty(
        name="Up",
        items=(
            ('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", ""),
            ('-X', "-X", ""), ('-Y', "-Y", ""), ('-Z', "-Z", "")
        ),
        default='Y'
    )

    def invoke(self, context, event):
        collection = bpy.data.collections.get(self.collection_name)
        if collection is None:
            self.report({'ERROR'}, "Collection not found. Invoke this command from its Outliner context menu.")
            return {'CANCELLED'}

        blend_path = bpy.data.filepath
        default_dir = os.path.dirname(blend_path) if blend_path else os.path.expanduser("~")
        self.filepath = os.path.join(default_dir, f"{collection.name}.fbx")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        source_collection = bpy.data.collections.get(self.collection_name)
        if source_collection is None:
            self.report({'ERROR'}, "Source collection no longer exists.")
            return {'CANCELLED'}

        # If invoked directly (e.g. from a menu with EXEC context or via script),
        # no file dialog was shown and filepath is empty — open it now.
        if not self.filepath:
            if context.window_manager is None:
                self.report({'ERROR'}, "No export path specified and no UI available to pick one.")
                return {'CANCELLED'}
            blend_path = bpy.data.filepath
            default_dir = os.path.dirname(blend_path) if blend_path else os.path.expanduser("~")
            self.filepath = os.path.join(default_dir, f"{source_collection.name}.fbx")
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}

        export_path = bpy.path.abspath(self.filepath)
        if not export_path:
            self.report({'ERROR'}, "No export path specified.")
            return {'CANCELLED'}
        if not export_path.lower().endswith(".fbx"):
            export_path += ".fbx"

        temp_scene = None
        builder = None
        try:
            temp_scene = bpy.data.scenes.new(
                name="__UNITY_FBX_EXPORT_TEMP__"
            )
            builder = ExportBuilder(context, temp_scene)
            builder.build(source_collection)

            export_objects = list(temp_scene.objects)
            if not export_objects:
                raise RuntimeError("The selected collection contains no exportable objects.")

            view_layer = temp_scene.view_layers[0]
            for obj in export_objects:
                obj.select_set(True, view_layer=view_layer)

            view_layer.objects.active = next(
                (obj for obj in export_objects if obj.get("UnityCollectionExportRoot")),
                export_objects[0]
            )

            with context.temp_override(
                scene=temp_scene,
                view_layer=view_layer,
                active_object=view_layer.objects.active,
                object=view_layer.objects.active,
                selected_objects=export_objects,
                selected_editable_objects=export_objects
            ):
                result = bpy.ops.export_scene.fbx(
                    filepath=export_path,
                    check_existing=False,
                    use_selection=True,
                    object_types={'EMPTY', 'MESH'},
                    use_mesh_modifiers=False,
                    axis_forward=self.axis_forward,
                    axis_up=self.axis_up,
                    apply_scale_options='FBX_SCALE_ALL',
                    use_space_transform=True,
                    bake_space_transform=False,
                    bake_anim=False,
                    add_leaf_bones=False,
                    path_mode='AUTO'
                )

            if 'FINISHED' not in result:
                raise RuntimeError("FBX exporter did not finish successfully.")

            message = (
                f"Exported: {os.path.basename(export_path)} | "
                f"Meshes: {len(builder.mesh_cache)} | "
                f"Instances: {builder.instance_count}"
            )
            if builder.warnings:
                message += f" | Warnings: {len(builder.warnings)}"
                for warning in builder.warnings[:5]:
                    print(f"[Unity Collection Exporter] {warning}")
            self.report({'INFO'}, message)
            return {'FINISHED'}

        except Exception as exc:
            traceback.print_exc()
            self.report({'ERROR'}, f"Export failed: {exc}")
            return {'CANCELLED'}

        finally:
            if temp_scene:
                for obj in list(temp_scene.objects):
                    bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.scenes.remove(temp_scene)

            if builder:
                for mesh in builder.created_meshes:
                    if mesh and mesh.users == 0:
                        bpy.data.meshes.remove(mesh)


# ------------------------------------------------------------------------
# Outliner context menu
# ------------------------------------------------------------------------

def outliner_context_menu(self, context):
    collection = getattr(context, "id", None)
    if not isinstance(collection, bpy.types.Collection):
        selected_ids = getattr(context, "selected_ids", ())
        collection = next(
            (item for item in selected_ids if isinstance(item, bpy.types.Collection)),
            None
        )
    if not isinstance(collection, bpy.types.Collection):
        return

    self.layout.separator()
    # Isolate INVOKE_DEFAULT to our own sub-layout so it doesn't leak into
    # other menu entries drawn after ours.
    col = self.layout.column()
    col.operator_context = 'INVOKE_DEFAULT'
    operator = col.operator(
        EXPORT_OT_unity_collection_fbx.bl_idname,
        text="Export Collection to Unity (.fbx)",
        icon='EXPORT'
    )
    operator.collection_name = collection.name


def menu_func_export(self, context):
    col = self.layout.column()
    col.operator_context = 'INVOKE_DEFAULT'
    col.operator(
        EXPORT_OT_unity_collection_fbx.bl_idname,
        text="Unity Collection (.fbx)"
    )


classes = (
    EXPORT_OT_unity_collection_fbx,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.OUTLINER_MT_collection.append(outliner_context_menu)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.OUTLINER_MT_collection.remove(outliner_context_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()