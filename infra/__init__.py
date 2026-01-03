# infra/ - Blender 連携の基盤層
#
# Blender API との橋渡しを担当。
# - メニュー登録・管理
# - オペレーター定義
# - イベント処理
# - 構造化ロギング

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from .logger import LoggerRegistry, get_logger, init_logger, profile_scope, shutdown_logger
from .registry import MenuRegistry


class PME_OT_mini_exec(Operator):
    """コマンド実行オペレーター。

    Pie Menu のアイテムクリック時に呼ばれる。
    """

    bl_idname = "wm.pme_mini_exec"
    bl_label = "PME Mini Execute"
    bl_options = {"INTERNAL"}

    command: StringProperty(
        name="Command",
        description="実行する Python コマンド",
        default="",
    )

    def execute(self, context):
        if self.command:
            try:
                exec(self.command)
            except Exception as e:
                self.report({"ERROR"}, f"実行エラー: {e}")
                return {"CANCELLED"}
        return {"FINISHED"}


# 登録するクラス
CLASSES = [
    PME_OT_mini_exec,
]


def register():
    """Blender へのクラス登録"""
    # ロガー初期化（最初に）
    init_logger()

    for cls in CLASSES:
        bpy.utils.register_class(cls)

    # メニューレジストリの初期化
    MenuRegistry.init()

    # 登録完了ログ
    log = get_logger("general")
    log.info("PME mini registered", classes=len(CLASSES))


def unregister():
    """Blender からのクラス登録解除"""
    MenuRegistry.clear()

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

    # ロガーシャットダウン（最後に）
    shutdown_logger()
