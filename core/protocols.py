# protocols.py - インターフェース定義
#
# Protocol を使った「緩い契約」。
# 継承なしで、必要なメソッドさえ持てば契約を満たす。
#
# 参考: PEP 544 - Protocols: Structural subtyping

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MenuSchema(Protocol):
    """メニューのデータスキーマ。

    責務:
      - メニューの設定値を保持
      - シリアライズ/デシリアライズ

    これは「データ」を表す。振る舞いは含まない。
    """

    @classmethod
    def type_id(cls) -> str:
        """メニュータイプの識別子 (例: "pie", "popup")"""
        ...

    def to_dict(self) -> dict[str, Any]:
        """辞書形式にエクスポート"""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MenuSchema":
        """辞書形式からインポート"""
        ...


@runtime_checkable
class MenuBehavior(Protocol):
    """メニューの振る舞い定義。

    責務:
      - メニューの動作特性を定義
      - ライフサイクルフック

    これは「ルール」を表す。データは含まない。
    """

    @property
    def fixed_num_items(self) -> bool:
        """アイテム数が固定か (Pie Menu = True)"""
        ...

    @property
    def max_items(self) -> int:
        """最大アイテム数"""
        ...

    def on_invoke(self, context: Any) -> None:
        """メニュー呼び出し時のフック"""
        ...


@runtime_checkable
class MenuView(Protocol):
    """メニューの描画担当。

    責務:
      - UI レイアウトの描画
      - ユーザー入力の処理

    これは「見た目」を表す。ビジネスロジックは含まない。
    """

    def draw_settings(self, layout: Any, schema: MenuSchema) -> None:
        """設定パネルの描画"""
        ...

    def draw_menu(self, layout: Any, schema: MenuSchema) -> None:
        """メニュー本体の描画"""
        ...
