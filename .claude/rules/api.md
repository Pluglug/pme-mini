# rules/api.md

pme.py 外部 API の設計指針。

---

## 1. 設計方針

### ファサードパターン

`pme.py` は**外部向けの唯一のエントリポイント**。

```python
# 推奨: pme ファサード経由
from pme_mini import pme
pme.execute("bpy.ops.mesh.primitive_cube_add()")

# 非推奨: 内部モジュールへの直接アクセス
from pme_mini.infra.registry import MenuRegistry  # 内部構造に依存
```

### 最小限の API

- 必要最小限のシンボルのみ公開
- 「あったら便利」は後回し
- 迷ったら公開しない

### 読み取り優先

- 外部から「読み取る」API は積極的に公開
- 外部から「書き換える」API は慎重に

---

## 2. Stability Levels

### Stable

- 互換性を維持する約束
- 外部スクリプト・他アドオンからの利用を想定
- 変更時は deprecation warning → 削除

### Experimental

- 変更・削除の可能性あり
- フィードバックを受けて Stable に昇格 or 削除
- v1.0 までに固める

### Internal

- 外部からの利用は非推奨
- 予告なく変更される
- `_` プレフィックスで明示

---

## 3. 現在の API 一覧

### Executor（Experimental）

| 関数 | 説明 |
|------|------|
| `execute(code, extra_globals)` | Python コードを実行 |
| `evaluate(expr, extra_globals)` | 式を評価して結果を返す |
| `ExecuteResult` | 実行結果のデータクラス |

### Menu Integration（Experimental）

| 関数 | 説明 |
|------|------|
| `find_menu(name)` | 名前でメニューを検索 |
| `list_menus()` | 全メニューのリスト |
| `invoke_menu(menu_or_name)` | メニューを呼び出し |
| `MenuHandle` | メニューの読み取り専用ハンドル |

### Poll Helpers（Experimental）

| 定数 | 値 |
|------|-----|
| `polls.MESH_EDIT` | `"C.mode == 'EDIT_MESH'"` |
| `polls.OBJECT_MODE` | `"C.mode == 'OBJECT'"` |
| `polls.SCULPT_MODE` | `"C.mode == 'SCULPT'"` |
| `polls.HAS_ACTIVE_OBJECT` | `"C.active_object is not None"` |
| `polls.HAS_SELECTED` | `"len(C.selected_objects) > 0"` |

### Internal

| シンボル | 説明 |
|---------|------|
| `_get_registry()` | Registry への直接アクセス（デバッグ用） |

---

## 4. 使用例

### 基本的なコード実行

```python
from pme_mini import pme

# コード実行
result = pme.execute("bpy.ops.mesh.primitive_cube_add()")
if not result.success:
    print(f"Error: {result.error_message}")

# 式の評価
is_edit = pme.evaluate("C.mode == 'EDIT_MESH'")
```

### メニュー操作

```python
from pme_mini import pme

# メニュー検索
menu = pme.find_menu("My Pie Menu")
if menu:
    print(f"Found: {menu.name}")

# 全メニュー一覧
for m in pme.list_menus():
    print(f"{m.name}: {m.type_id}")
```

### Poll ヘルパー

```python
from pme_mini import pme

# 条件チェック
if pme.evaluate(pme.polls.MESH_EDIT):
    # Edit Mode 専用の処理
    pme.execute("bpy.ops.mesh.select_all(action='SELECT')")
```

---

## 5. PME 本体との対比

| 機能 | PME mini | PME 本体 |
|------|----------|---------|
| execute | `pme.execute()` | `pme.context.exe()` → `pme.execute()` |
| evaluate | `pme.evaluate()` | `pme.context.eval()` → `pme.evaluate()` |
| find_menu | `pme.find_menu()` | 未実装 → 将来 `pme.find_pm()` |
| invoke | `pme.invoke_menu()` | `WM_OT_pme_user_pie_menu_call` |

PME 本体では:
- 現状 `pme.context` が内部実装を公開している
- 将来は PME mini と同様のファサードに移行予定

---

## 6. 設計原則

### 1. 内部構造を隠蔽する

```python
# ✅ 良い: ハンドルで抽象化
@dataclass
class MenuHandle:
    name: str
    type_id: str

def find_menu(name: str) -> MenuHandle | None:
    schema = MenuRegistry.get_menu(name)
    return MenuHandle(name=schema.name, ...)  # 内部を隠蔽

# ❌ 悪い: 内部オブジェクトを直接返す
def find_menu(name: str) -> PieMenuSchema | None:
    return MenuRegistry.get_menu(name)  # 内部構造が露出
```

### 2. エラーハンドリングを明確に

```python
# execute: 例外を吸収して Result を返す
result = pme.execute(code)
if not result.success:
    handle_error(result.error_message)

# evaluate: 例外をそのまま投げる
try:
    value = pme.evaluate(expr)
except NameError as e:
    handle_error(e)
```

### 3. 将来の拡張を考慮

```python
@dataclass
class MenuHandle:
    name: str
    type_id: str
    enabled: bool = True
    # 将来の拡張（フィールド追加は後方互換）
    # hotkey: str | None = None
    # tag: str | None = None
```
