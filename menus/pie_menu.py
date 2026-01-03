# pie_menu.py - Pie Menu の振る舞いと描画
#
# Protocol を満たす具体的な実装。
# 継承ではなく「契約を満たすこと」で型として扱える。

from typing import Any

from ..core import PieMenuSchema


class PieMenuBehavior:
    """Pie Menu の振る舞い定義。

    MenuBehavior Protocol を満たす。
    継承なしで、必要なプロパティ・メソッドを実装するだけでよい。
    """

    @property
    def fixed_num_items(self) -> bool:
        """Pie Menu は 8 スロット固定"""
        return True

    @property
    def max_items(self) -> int:
        """最大 8 アイテム"""
        return 8

    def on_invoke(self, context: Any) -> None:
        """Pie Menu 呼び出し時のフック。

        将来的に:
          - フリック設定の適用
          - radius のオーバーライド
          - 履歴記録
        などを行う。
        """
        pass


class PieMenuView:
    """Pie Menu の描画担当。

    MenuView Protocol を満たす。
    bpy.types.UILayout を受け取って描画するだけの薄いクラス。
    """

    def draw_settings(self, layout: Any, schema: PieMenuSchema) -> None:
        """設定パネルの描画。

        エディタ画面での Pie Menu 設定表示。
        """
        # layout は bpy.types.UILayout
        col = layout.column()
        col.label(text=f"Pie Menu: {schema.name}")

        # 基本設定
        box = col.box()
        box.label(text="基本設定", icon="SETTINGS")

        row = box.row()
        row.label(text=f"Radius: {schema.radius}")
        row.label(text=f"Flick: {schema.flick}")

    def draw_menu(self, layout: Any, schema: PieMenuSchema) -> None:
        """メニュー本体の描画。

        実際の Pie Menu 表示時に呼ばれる。
        """
        # Pie Menu の 8 スロットを表示
        pie = layout.menu_pie()

        for i, item in enumerate(schema.items):
            if item.name:
                pie.operator(
                    "wm.pme_mini_exec",
                    text=item.name,
                    icon=item.icon,
                ).command = item.command
            else:
                # 空スロット
                pie.separator()


# -----------------------------------------------------------------------------
# 型チェックのデモ（テスト用）
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    from ..core.protocols import MenuBehavior, MenuView

    # Protocol を満たしているか確認
    behavior = PieMenuBehavior()
    view = PieMenuView()

    print(f"PieMenuBehavior は MenuBehavior か: {isinstance(behavior, MenuBehavior)}")
    print(f"PieMenuView は MenuView か: {isinstance(view, MenuView)}")
