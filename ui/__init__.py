# ui/ - Blender UI 部品
#
# サイドバーパネル、プロパティ表示など、
# Blender の UI システムを使った画面部品。

import bpy

from .panels import PME_OT_mini_create, PME_PT_mini_panel


CLASSES = [
    PME_OT_mini_create,  # オペレーターを先に登録
    PME_PT_mini_panel,
]


def register():
    """UI クラスの登録"""
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    """UI クラスの登録解除"""
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
