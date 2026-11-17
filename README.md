# Captain FBX Exporter

Blender add-on for exporting a character model and its animation Actions as FBX files for Unity.

## Requirements

- Blender 5.2 or newer (the add-on is declared for Blender 5.2)
- The character armature and its mesh objects in the same Blender scene
- The built-in FBX exporter enabled in Blender

## Features

- Export the selected character model without animation
- Export the active Action or every Action as separate FBX files
- Export a collection hierarchy (with child collections and collection instances) to a Unity-ready FBX, preserving object names and sharing mesh geometry between instances
- Use the Action name for the output FBX filename
- Rename the Blender scene during each animation export so Unity imports the clip with a useful name instead of `Scene`
- Optional text dump of the object and bone hierarchies for debugging
- Export scale option `FBX_SCALE_UNITS`; leaf bones are disabled

## Installation

1. Download or clone this repository.
2. Install the `captain_fbx_exporter` folder as a Blender add-on package. For a ZIP installation, the ZIP must contain the `captain_fbx_exporter` folder at its root.
3. In Blender, open **Edit → Preferences → Add-ons** (or **Get Extensions**, depending on the Blender build), choose **Install from Disk**, and select the ZIP.
4. Enable **Captain FBX Exporter**.
5. In the 3D View, open the Sidebar with `N` and select the **Captain Export** tab.

If Blender's installer does not accept the repository ZIP layout, create a ZIP containing the `captain_fbx_exporter` package folder itself, then install that ZIP.

## Usage

1. Select the character's **Armature** and make it the active object.
2. Set **Export folder** to the destination directory.
3. To export the model, set **Model name** and click **Export model**.
4. To export the active Action only, leave **Export All Actions** disabled and make the required Action active on the armature.
5. To export all Actions, enable **Export All Actions**.
6. Enable **Save Hierarchy Debug Dump** only when debugging is needed; a `_blender.txt` file is written beside each animation FBX.
7. Click **Export Animations**.

### Exporting a collection

The collection exporter is available from the **Outliner** context menu and from **File → Export**.

1. In the **Outliner**, right-click the collection you want to export and choose **Export Collection to Unity (.fbx)**.
2. Pick the destination file in the file dialog.
3. Alternatively, use **File → Export → Unity Collection (.fbx)** from the top menu.

The exporter writes a temporary export scene, walks the collection hierarchy (including child collections), expands collection instances (including instances with modifiers such as Array), and exports the result as FBX with `FBX_SCALE_ALL` and `use_space_transform=True`. The temporary scene is removed afterwards.

- Object names inside instanced collections are preserved (`tube`, `fitting`, …) instead of being replaced by the instancer's name. Numeric suffixes are added only on name collisions.
- Geometry is shared between instances: N collection copies that reference the same source mesh become N objects referencing one `bpy.data.meshes` datablock, which FBX writes as one `Geometry` node + N `Model` nodes, and Unity imports as one Mesh asset + N GameObjects.
- Modifiers on a collection instancer are evaluated by the depsgraph. To keep mesh sharing, disable **Realize Instances** on Array modifiers that spread a collection instance — otherwise every copy becomes distinct geometry.
- Recursive collection instances are detected and skipped with a warning.

## Output

- `Captain_Model.fbx` (or the configured model filename)
- One `<ActionName>.fbx` file per exported animation
- Optional `<ActionName>_blender.txt` hierarchy dumps
- `<CollectionName>.fbx` (or the filename chosen in the file dialog) when exporting a collection

The add-on temporarily parents the armature to an Empty while exporting animation clips and restores the armature parent, transforms, active Action, scene frame range, current frame, scene name, and selection afterwards.

## Project structure

```text
captain_fbx_exporter/
├── __init__.py          # Add-on metadata and registration
├── settings.py          # Export settings
├── common.py            # Shared helpers and hierarchy dump
├── model_export.py      # Model FBX export operator
├── animation_export.py  # Animation FBX export operator
├── collection_export.py # Collection hierarchy FBX export operator
└── ui.py                # Sidebar panel
```

## Notes and limitations

- This exporter is designed around a Generic-style character rig workflow; it does not configure Unity import settings or create Unity Animator Controllers.
- In **Export Animations** mode, every Action in `bpy.data.actions` is considered. If the file contains unrelated Actions, they will also be exported.
- Action names are sanitized for filenames. Avoid duplicate Action names that sanitize to the same filename, because one export can overwrite another.
- Test the generated FBX files in the target Unity version before using the add-on in production.
- The collection exporter exports static geometry only (meshes and empties). Armatures, cameras, lights, and other object types inside the exported collection are ignored.
- If a collection is expanded as an instance and also appears as a child of the exported collection, the child traversal skips it to avoid duplicate geometry. A warning is printed in that case.
- Modifiers that change topology per copy (Array with **Merge**, Boolean, Remesh, etc.) produce one evaluated mesh per instance, so those copies do not share geometry and become separate Mesh assets in Unity.

## License

No license is included yet. Choose a license before publishing the repository if you want to grant others explicit reuse rights.
