# PME Mini - 最小限の Pie Menu Editor
# 設計実験のためのプロトタイプ
#
# 設計原則:
#   1. Core は Blender 非依存
#   2. Protocol による緩い契約
#   3. dataclass によるスキーマ定義
#   4. 継承より合成

bl_info = {
    "name": "PME Mini",
    "author": "PME2 Design Experiment",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > PME Mini",
    "description": "最小限の Pie Menu Editor - 設計実験用",
    "category": "Interface",
}

# -----------------------------------------------------------------------------
# モジュールのインポート順序
# -----------------------------------------------------------------------------
# 1. core (Blender 非依存)
# 2. menus (メニュータイプの実装)
# 3. infra (Blender 連携)
# 4. ui (パネル、オペレーター)


def register():
    """アドオン登録"""
    from . import infra, ui

    infra.register()
    ui.register()

    print("PME Mini: 登録完了")


def unregister():
    """アドオン登録解除"""
    from . import infra, ui

    ui.unregister()
    infra.unregister()

    print("PME Mini: 登録解除完了")
