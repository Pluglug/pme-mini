# rules/development.md

開発の進め方とコーディング規約。

---

## 1. 開発フロー

### 機能追加の手順

1. **CLAUDE.md のマイルストーンを確認**
2. **小さな単位で実装**（1 機能 = 1 コミット目安）
3. **Blender で動作確認**
4. **必要に応じてドキュメント更新**

### コミットメッセージ

```
[mini] 機能の簡潔な説明

- 詳細 1
- 詳細 2
```

例:
```
[mini] Add JSON persistence for menus

- Implement save_menus() / load_menus() in infra/
- Call load on register, save on menu creation
```

---

## 2. コーディング規約

### 言語

- **コード**: 英語（変数名、関数名）
- **コメント**: 日本語（docstring 含む）
- **ドキュメント**: 日本語

### クラス定義

```python
@dataclass
class PieMenuSchema:
    """
    Pie Menu のスキーマ。

    PME の PMItem に相当するが、PropertyGroup ではなく
    純粋なデータクラス。
    """

    name: str = ""
    radius: int = -1  # -1 = デフォルト値を使用
```

### Protocol 実装

```python
class PieMenuBehavior:
    """
    Pie Menu の振る舞い定義。

    MenuBehavior Protocol を満たす。
    継承なしで、必要なプロパティ・メソッドを実装するだけでよい。
    """

    @property
    def fixed_num_items(self) -> bool:
        """Pie Menu は 8 スロット固定"""
        return True
```

### インポート順序

```python
# 1. 標準ライブラリ
from dataclasses import dataclass
from typing import Any, Protocol

# 2. Blender（infra/ui のみ）
import bpy
from bpy.types import Operator, Panel

# 3. 同パッケージ
from .registry import MenuRegistry

# 4. 親パッケージ
from ..core import MenuSchema
from ..menus import PieMenuBehavior
```

---

## 3. ファイル命名規則

| 種類 | 命名 | 例 |
|------|------|-----|
| モジュール | snake_case | `pie_menu.py`, `registry.py` |
| クラス | PascalCase | `PieMenuSchema`, `MenuRegistry` |
| Protocol | PascalCase | `MenuSchema`, `MenuBehavior` |
| 定数 | UPPER_SNAKE | `MAX_ITEMS = 8` |

### Blender クラス命名

```python
# Operator: {PREFIX}_OT_{name}
class PME_OT_mini_exec(Operator):
    bl_idname = "wm.pme_mini_exec"

# Panel: {PREFIX}_PT_{name}
class PME_PT_mini_panel(Panel):
    bl_idname = "PME_PT_mini_panel"
```

---

## 4. テスト方針

### 手動テスト（現時点）

1. **アドオン有効化**
   - [ ] エラーなく有効化できる
   - [ ] サイドバーに「PME Mini」タブが表示される

2. **基本操作**
   - [ ] 「新規 Pie Menu」ボタンが動作
   - [ ] 作成したメニューがリストに表示される

3. **Reload Scripts**
   - [ ] F3 → Reload Scripts でエラーなし
   - [ ] 状態がリセットされる（永続化実装前は想定通り）

### 将来: 自動テスト

core/ 層は Blender 非依存なので、pytest でテスト可能:

```python
# tests/test_schemas.py
def test_pie_menu_schema_serialization():
    menu = PieMenuSchema(name="Test", radius=100)
    data = menu.to_dict()
    restored = PieMenuSchema.from_dict(data)
    assert restored.name == "Test"
    assert restored.radius == 100
```

---

## 5. 設計判断の記録

重要な設計判断は `.claude/rules/decisions.md` に記録する（今後作成）。

フォーマット:
```markdown
## YYYY-MM-DD: 判断タイトル

### 背景
なぜこの判断が必要だったか

### 選択肢
1. 選択肢 A — メリット / デメリット
2. 選択肢 B — メリット / デメリット

### 決定
選択肢 X を採用

### 理由
なぜその選択肢を選んだか
```
