# Captain FBX Exporter

Blender add-on for exporting a character model and its animation Actions as FBX files for Unity.

## Requirements

- Blender 5.2 or newer (the add-on is declared for Blender 5.2)
- The character armature and its mesh objects in the same Blender scene
- The built-in FBX exporter enabled in Blender

## Features

- Export the selected character model without animation
- Export the active Action or every Action as separate FBX files
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
2. Set **Папка экспорта** to the destination directory.
3. To export the model, set **Имя модели** and click **Экспорт модели**.
4. To export the active Action only, leave **Экспорт всех анимаций** disabled and make the required Action active on the armature.
5. To export all Actions, enable **Экспорт всех анимаций**.
6. Enable **Сохранять дамп иерархии** only when debugging is needed; a `_blender.txt` file is written beside each animation FBX.
7. Click **Экспорт анимаций**.

## Output

- `Captain_Model.fbx` (or the configured model filename)
- One `<ActionName>.fbx` file per exported animation
- Optional `<ActionName>_blender.txt` hierarchy dumps

The add-on temporarily parents the armature to an Empty while exporting animation clips and restores the armature parent, transforms, active Action, scene frame range, current frame, scene name, and selection afterwards.

## Project structure

```text
captain_fbx_exporter/
├── __init__.py          # Add-on metadata and registration
├── settings.py          # Export settings
├── common.py            # Shared helpers and hierarchy dump
├── model_export.py      # Model FBX export operator
├── animation_export.py  # Animation FBX export operator
└── ui.py                # Sidebar panel
```

## Notes and limitations

- This exporter is designed around a Generic-style character rig workflow; it does not configure Unity import settings or create Unity Animator Controllers.
- In **Экспорт всех анимаций** mode, every Action in `bpy.data.actions` is considered. If the file contains unrelated Actions, they will also be exported.
- Action names are sanitized for filenames. Avoid duplicate Action names that sanitize to the same filename, because one export can overwrite another.
- Test the generated FBX files in the target Unity version before using the add-on in production.

## License

No license is included yet. Choose a license before publishing the repository if you want to grant others explicit reuse rights.
