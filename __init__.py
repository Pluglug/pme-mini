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
# use_reload パターン
# -----------------------------------------------------------------------------
# Blender の Reload Scripts (F3) で再読み込みされた場合、
# すでに import 済みのモジュールをリロードする必要がある。
# locals() に "addon" があるかどうかで初回ロードか再ロードかを判定。

use_reload = "addon" in locals()
if use_reload:
    import importlib

    importlib.reload(locals()["addon"])  # type: ignore
    del importlib

from . import addon

# -----------------------------------------------------------------------------
# モジュール初期化
# -----------------------------------------------------------------------------
# パターンにマッチするモジュールを依存順にロード。
# レイヤ順序: core (0) → menus (1) → infra (2) → ui (3)

addon.init_addon(
    module_patterns=[
        "core.*",
        "menus.*",
        "infra.*",
        "ui.*",
    ],
    use_reload=use_reload,
    version=bl_info["version"],
)


def register():
    """アドオン登録"""
    addon.register_modules()
    print("PME Mini: 登録完了")


def unregister():
    """アドオン登録解除"""
    addon.unregister_modules()
    print("PME Mini: 登録解除完了")
