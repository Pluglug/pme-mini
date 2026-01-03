# schemas.py - データ構造の定義
#
# dataclass を使った型安全なスキーマ。
# IDE 補完が効く、バリデーションしやすい。

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MenuItemSchema:
    """メニューアイテムのスキーマ。

    PME の PMIItem に相当するが、PropertyGroup ではなく純粋なデータクラス。
    """

    name: str = ""
    icon: str = "NONE"
    command: str = ""
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MenuItemSchema":
        return cls(**data)


@dataclass
class PieMenuSchema:
    """Pie Menu のスキーマ。

    PME の PMItem + "pm" タイプのプロパティに相当。
    """

    # 基本情報
    name: str = "New Pie Menu"
    enabled: bool = True

    # Pie Menu 固有の設定
    radius: int = -1  # -1 = デフォルト値を使用
    flick: bool = True
    confirm: int = -1
    threshold: int = -1

    # アイテム（固定8スロット）
    items: list[MenuItemSchema] = field(
        default_factory=lambda: [MenuItemSchema() for _ in range(8)],
    )

    @classmethod
    def type_id(cls) -> str:
        return "pie"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type_id(),
            "name": self.name,
            "enabled": self.enabled,
            "radius": self.radius,
            "flick": self.flick,
            "confirm": self.confirm,
            "threshold": self.threshold,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PieMenuSchema":
        items_data = data.pop("items", [])
        data.pop("type", None)  # type_id は不要
        schema = cls(**data)
        schema.items = [MenuItemSchema.from_dict(item) for item in items_data]
        return schema


# -----------------------------------------------------------------------------
# 使用例（テスト用）
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # スキーマの作成
    menu = PieMenuSchema(name="My Pie Menu", radius=100)

    # アイテムの設定
    menu.items[0] = MenuItemSchema(
        name="Cube",
        icon="MESH_CUBE",
        command="bpy.ops.mesh.primitive_cube_add()",
    )

    # シリアライズ
    data = menu.to_dict()
    print("Serialized:", data)

    # デシリアライズ
    restored = PieMenuSchema.from_dict(data)
    print("Restored:", restored.name, restored.items[0].name)
