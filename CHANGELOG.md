# Changelog

## 1.2.0
- Added collection hierarchy export: right-click a collection in the Outliner or use File → Export to write it, its child collections and its collection instances to a Unity-ready FBX.
- Collection instances that carry modifiers (e.g. Array) are evaluated through the depsgraph, and mesh datablocks are shared between copies so FBX/Unity see one Mesh asset per logical detail.
- Object names inside instanced collections are preserved; numeric suffixes are added only on name collisions.
- Recursive collection instances are detected and skipped with a warning.

## 1.1.1
- Translate all cyrillic names to latin.

## 1.1.0
- Split the add-on into modules for shared helpers, settings, model export, animation export, and UI.
- Added GitHub README, repository ignore rules, and changelog.
- Kept the existing FBX export options and scene-name workaround for Unity clip naming.
