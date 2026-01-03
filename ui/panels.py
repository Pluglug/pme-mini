# panels.py - サイドバーパネル
#
# 3D View のサイドバーに表示するパネル。
# メニューの一覧表示と簡易編集機能。

import bpy
from bpy.types import Panel

from ..infra.registry import MenuRegistry


class PME_PT_mini_panel(Panel):
    """PME Mini のサイドバーパネル。

    メニューの作成、一覧、設定表示を行う。
    """

    bl_idname = "PME_PT_mini_panel"
    bl_label = "PME Mini"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PME Mini"

    def draw(self, context):
        layout = self.layout

        # メニュー作成ボタン
        row = layout.row()
        row.operator("wm.pme_mini_create", text="新規 Pie Menu", icon="ADD")

        layout.separator()

        # 登録済みメニューの一覧
        menus = MenuRegistry.list_menus()

        if not menus:
            layout.label(text="メニューがありません", icon="INFO")
            return

        for menu in menus:
            box = layout.box()

            # ヘッダー行
            row = box.row()
            row.label(text=menu.name, icon="MESH_CIRCLE")

            # メニュータイプ情報を取得して設定を描画
            type_info = MenuRegistry.get_type(menu.type_id())
            if type_info:
                type_info.view.draw_settings(box, menu)


# -----------------------------------------------------------------------------
# メニュー作成オペレーター
# -----------------------------------------------------------------------------
class PME_OT_mini_create(bpy.types.Operator):
    """新しい Pie Menu を作成"""

    bl_idname = "wm.pme_mini_create"
    bl_label = "Create Pie Menu"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # ユニークな名前を生成
        existing = [m.name for m in MenuRegistry.list_menus()]
        base_name = "Pie Menu"
        name = base_name
        counter = 1

        while name in existing:
            counter += 1
            name = f"{base_name} {counter}"

        # メニューを作成
        menu = MenuRegistry.create_menu("pie", name)

        if menu:
            self.report({"INFO"}, f"作成: {name}")
        else:
            self.report({"ERROR"}, "作成に失敗しました")
            return {"CANCELLED"}

        return {"FINISHED"}


# パネルと一緒に登録するクラス
# ui/__init__.py の CLASSES に追加する必要あり
