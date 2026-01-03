# rules/testing.md

PME mini のテスト戦略。

---

## 1. テストの分類

### Unit Tests（Blender 不要）

pytest + fake-bpy-module で実行可能。

| 対象 | 内容 |
|------|------|
| 純粋なロジック | ユーティリティ関数、定数 |
| シリアライズ | `to_dict()` / `from_dict()` の往復 |
| パース処理 | 文字列パース、エンコード |
| 互換性修正 | マイグレーション関数 |

```bash
pytest tests/unit/
```

### Blender Tests（バックグラウンドモード）

`blender --background --python` で実行。

| 対象 | 内容 |
|------|------|
| アドオン有効化 | `register()` が通るか |
| クラス登録 | PropertyGroup, Operator, Panel |
| JSON I/O | エクスポート/インポート |
| オペレーター実行 | 基本的な Pie Menu 呼び出し |

```bash
blender --background --python tests/blender/test_registration.py
```

### Manual Tests（GUI 必要）

自動化困難。チェックリストで管理。

- UI レイアウトの確認
- モーダルオペレーターの動作
- Pie Menu の見た目

---

## 2. ディレクトリ構成

```
pme_mini/
├── tests/
│   ├── unit/                    # pytest (Blender 不要)
│   │   ├── test_schemas.py
│   │   └── test_serialization.py
│   ├── blender/                 # Blender --background
│   │   ├── test_registration.py
│   │   ├── test_operators.py
│   │   └── test_json_io.py
│   └── conftest.py              # pytest fixtures
├── scripts/
│   └── run_blender_tests.py     # Blender テストランナー
```

---

## 3. テスト例

### Unit Test: Schema のラウンドトリップ

```python
# tests/unit/test_schemas.py
from pme_mini.core.schemas import PieMenuSchema, MenuItemSchema

def test_pie_menu_roundtrip():
    """Schema の to_dict/from_dict が正しく往復できるか"""
    menu = PieMenuSchema(name="Test", radius=100)
    menu.items[0] = MenuItemSchema(name="Cube", icon="MESH_CUBE")

    data = menu.to_dict()
    restored = PieMenuSchema.from_dict(data)

    assert restored.name == "Test"
    assert restored.radius == 100
    assert restored.items[0].name == "Cube"
```

### Blender Test: アドオン有効化

```python
# tests/blender/test_registration.py
"""
blender --background --python tests/blender/test_registration.py
"""
import bpy
import sys

def test_addon_enable():
    try:
        bpy.ops.preferences.addon_enable(module='pme_mini')
        print("✅ Addon enabled successfully")

        # クラス数の確認
        from pme_mini import infra, ui
        print(f"  Registered: infra={len(infra.CLASSES)}, ui={len(ui.CLASSES)}")

        return 0
    except Exception as e:
        print(f"❌ Addon enable failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_addon_enable())
```

---

## 4. CI/CD 統合（将来）

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install pytest fake-bpy-module-latest
      - run: pytest tests/unit/

  blender-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: nytimes/blender-action@v1
        with:
          blender-version: '4.2.0'
      - run: blender --background --python tests/blender/test_registration.py
```

---

## 5. 優先順位

| 優先度 | 対象 | 理由 |
|--------|------|------|
| 🔴 高 | JSON 互換性 | PME1 からのマイグレーション保証 |
| 🔴 高 | アドオン有効化 | 基本的な動作保証 |
| 🟡 中 | ParsedData パース | Reload Scripts 問題の検出 |
| 🟡 中 | Pie Menu 呼び出し | 基本機能の動作確認 |
| 🟢 低 | UI レイアウト | 見た目は手動確認で十分 |

---

## 6. 参照

- `pie_menu_editor/.claude/rules/testing.md` — PME2 本体のテストガイド
- pytest documentation: https://docs.pytest.org/
- fake-bpy-module: https://github.com/nutti/fake-bpy-module
