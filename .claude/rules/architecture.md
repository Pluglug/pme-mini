# rules/architecture.md

PME mini のアーキテクチャルール。

---

## 1. レイヤ構造

```
ui      (3) ← Blender UI（Panel, UIList）
infra   (2) ← Blender 連携（Operator, Registry, 永続化）
menus   (1) ← メニュータイプ実装（Behavior, View）
core    (0) ← Blender 非依存（Protocol, Schema）
```

### 依存ルール

| From | To | 許可 |
|------|-----|------|
| ui | infra, menus, core | ✅ |
| infra | menus, core | ✅ |
| menus | core | ✅ |
| core | (なし) | ✅ |
| core | 他のレイヤ | ❌ 禁止 |

### 各レイヤの責務

#### core/ — Blender 非依存

```python
# ✅ 許可
from dataclasses import dataclass
from typing import Protocol, Any

# ❌ 禁止
import bpy  # Blender 依存は禁止
```

**配置するもの**:
- Protocol 定義（`MenuSchema`, `MenuBehavior`, `MenuView`）
- dataclass スキーマ（`PieMenuSchema`, `MenuItemSchema`）
- 純粋な Python ロジック

#### menus/ — メニュータイプ実装

```python
# ✅ 許可
from ..core import PieMenuSchema, MenuBehavior
from typing import Any  # bpy.types.UILayout を Any で受ける
```

**配置するもの**:
- `*Behavior` クラス（振る舞いルール）
- `*View` クラス（描画ロジック）

#### infra/ — Blender 連携

```python
# ✅ 許可
import bpy
from bpy.types import Operator
from ..core import MenuSchema
from ..menus import PieMenuBehavior
```

**配置するもの**:
- Operator クラス
- `MenuRegistry`（メニュー登録）
- ファイル I/O、永続化

#### ui/ — Blender UI

```python
# ✅ 許可
import bpy
from bpy.types import Panel
from ..infra.registry import MenuRegistry
```

**配置するもの**:
- Panel クラス
- UIList クラス

---

## 2. Protocol パターン

### 基本原則

継承ではなく「契約を満たすこと」で型として扱う。

```python
# Protocol 定義（core/protocols.py）
@runtime_checkable
class MenuSchema(Protocol):
    @classmethod
    def type_id(cls) -> str: ...
    def to_dict(self) -> dict[str, Any]: ...

# 実装（core/schemas.py）— 継承なし
@dataclass
class PieMenuSchema:
    name: str = "New Pie Menu"

    @classmethod
    def type_id(cls) -> str:
        return "pie"

    def to_dict(self) -> dict[str, Any]:
        return {...}

# 型チェック
schema: MenuSchema = PieMenuSchema()  # ✅ 型として通る
isinstance(schema, MenuSchema)         # ✅ True（runtime_checkable）
```

### Protocol を使う場面

| 場面 | Protocol を使う理由 |
|------|-------------------|
| 関数の引数型 | 具体的な実装に依存しない |
| Registry の戻り値 | 複数のメニュータイプを統一的に扱う |
| テストのモック | 本物の実装なしでテスト可能 |

---

## 3. Registry パターン

### 目的

メニュータイプとインスタンスを一元管理する。

```python
class MenuRegistry:
    _types: dict[str, MenuTypeInfo] = {}   # type_id -> TypeInfo
    _menus: dict[str, MenuSchema] = {}     # name -> Schema

    @classmethod
    def register_type(cls, schema_class, behavior, view): ...

    @classmethod
    def create_menu(cls, type_id: str, name: str) -> MenuSchema: ...
```

### PME 本体との対比

| PME mini | PME 本体 | 改善点 |
|----------|---------|--------|
| `MenuRegistry` | `PMEPreferences.editors` | クラス変数 → 明示的なレジストリ |
| `MenuTypeInfo` | Editor クラス | Schema/Behavior/View を分離 |
| `create_menu()` | 直接 PM 作成 | ファクトリメソッドで統一 |

---

## 4. 将来の拡張ポイント

### 新しいメニュータイプの追加

```python
# 1. core/schemas.py に Schema を追加
@dataclass
class RegularMenuSchema:
    @classmethod
    def type_id(cls) -> str:
        return "regular"
    ...

# 2. menus/regular_menu.py に Behavior と View を追加
class RegularMenuBehavior:
    @property
    def fixed_num_items(self) -> bool:
        return False  # 可変長
    ...

# 3. infra/registry.py の init() で登録
MenuRegistry.register_type(
    RegularMenuSchema,
    RegularMenuBehavior(),
    RegularMenuView(),
)
```

### 外部プラグインからの登録（将来）

```python
# 外部アドオンから
from pme_mini.infra.registry import MenuRegistry
from pme_mini.core import MenuSchema, MenuBehavior, MenuView

MenuRegistry.register_type(MyCustomSchema, MyBehavior(), MyView())
```
