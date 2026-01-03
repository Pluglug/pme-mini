# registry.py - メニュー登録・管理
#
# メニュータイプと実際のメニューインスタンスを管理する。
# PME 本体の「Editor を PMEPreferences.editors に登録する」
# パターンの代替案。

from typing import Any

from ..core import MenuBehavior, MenuSchema, MenuView, PieMenuSchema
from ..menus import PieMenuBehavior, PieMenuView


class MenuTypeInfo:
    """メニュータイプの情報をまとめたコンテナ。

    Schema, Behavior, View を一つにバンドル。
    """

    def __init__(
        self,
        schema_class: type,
        behavior: MenuBehavior,
        view: MenuView,
    ):
        self.schema_class = schema_class
        self.behavior = behavior
        self.view = view

    @property
    def type_id(self) -> str:
        return self.schema_class.type_id()


class MenuRegistry:
    """メニュータイプとインスタンスのレジストリ。

    シングルトン的に使うが、テスト時は init()/clear() で
    状態をリセットできる。
    """

    # メニュータイプ: type_id -> MenuTypeInfo
    _types: dict[str, MenuTypeInfo] = {}

    # メニューインスタンス: name -> MenuSchema
    _menus: dict[str, MenuSchema] = {}

    @classmethod
    def init(cls) -> None:
        """レジストリの初期化。

        組み込みのメニュータイプを登録する。
        """
        cls._types.clear()
        cls._menus.clear()

        # Pie Menu タイプを登録
        cls.register_type(
            PieMenuSchema,
            PieMenuBehavior(),
            PieMenuView(),
        )

    @classmethod
    def clear(cls) -> None:
        """レジストリのクリア"""
        cls._types.clear()
        cls._menus.clear()

    @classmethod
    def register_type(
        cls,
        schema_class: type,
        behavior: MenuBehavior,
        view: MenuView,
    ) -> None:
        """メニュータイプを登録。

        将来的には外部プラグインからも呼べる API にする想定。
        """
        info = MenuTypeInfo(schema_class, behavior, view)
        cls._types[info.type_id] = info

    @classmethod
    def get_type(cls, type_id: str) -> MenuTypeInfo | None:
        """メニュータイプ情報を取得"""
        return cls._types.get(type_id)

    @classmethod
    def create_menu(cls, type_id: str, name: str, **kwargs: Any) -> MenuSchema | None:
        """新しいメニューを作成して登録。

        Args:
            type_id: メニュータイプ ID ("pie" など)
            name: メニュー名
            **kwargs: スキーマに渡す追加パラメータ

        Returns:
            作成されたスキーマ、またはタイプが見つからない場合 None
        """
        type_info = cls.get_type(type_id)
        if not type_info:
            return None

        schema = type_info.schema_class(name=name, **kwargs)
        cls._menus[name] = schema
        return schema

    @classmethod
    def get_menu(cls, name: str) -> MenuSchema | None:
        """名前でメニューを取得"""
        return cls._menus.get(name)

    @classmethod
    def list_menus(cls) -> list[MenuSchema]:
        """全メニューのリスト"""
        return list(cls._menus.values())

    @classmethod
    def remove_menu(cls, name: str) -> bool:
        """メニューを削除"""
        if name in cls._menus:
            del cls._menus[name]
            return True
        return False
