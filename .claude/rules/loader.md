# rules/loader.md

addon.py ローダーの設計指針。

---

## 1. 目的

PME 本体の `init_addon` / `register_modules` パターンを学び、
PME mini でもクリーンなモジュールロードを実現する。

---

## 2. 現状の構造

### 現在の register フロー

```python
# __init__.py
def register():
    from . import infra
    from . import ui

    infra.register()  # Operator 登録 + MenuRegistry.init()
    ui.register()     # Panel 登録

def unregister():
    from . import ui
    from . import infra

    ui.unregister()
    infra.unregister()  # MenuRegistry.clear()
```

### 問題点

1. **import 順序が暗黙的** — 依存関係がコードに埋もれている
2. **reload 対応がない** — Reload Scripts で状態が残る可能性
3. **エラーハンドリングが弱い** — 途中で失敗すると不整合

---

## 3. 目標の構造

### addon.py の導入

```python
# addon.py
"""
モジュールロードと登録を一元管理。
"""

# モジュールパターン（ロード順序を明示）
MODULE_PATTERNS = [
    "core.*",      # 最初にロード（依存なし）
    "menus.*",     # core に依存
    "infra.*",     # menus, core に依存
    "ui.*",        # infra, menus, core に依存
]

_modules: list = []

def init_addon():
    """モジュールの収集とロード"""
    global _modules
    _modules = collect_modules(MODULE_PATTERNS)
    load_modules(_modules)

def register_modules():
    """各モジュールの register() を呼び出し"""
    for mod in _modules:
        if hasattr(mod, "register"):
            mod.register()

def unregister_modules():
    """各モジュールの unregister() を逆順で呼び出し"""
    for mod in reversed(_modules):
        if hasattr(mod, "unregister"):
            mod.unregister()
```

### __init__.py の変更

```python
# __init__.py
from . import addon

def register():
    addon.init_addon()
    addon.register_modules()

def unregister():
    addon.unregister_modules()
```

---

## 4. reload 対応

### use_reload パターン

```python
# __init__.py
use_reload = "addon" in locals()

if use_reload:
    import importlib
    importlib.reload(locals()["addon"])
    del importlib

from . import addon

def register():
    addon.init_addon(use_reload=use_reload)
    addon.register_modules()
```

### init_addon での reload 処理

```python
def init_addon(use_reload: bool = False):
    global _modules

    if use_reload:
        # 既存モジュールをリロード
        for mod in _modules:
            importlib.reload(mod)
    else:
        # 新規ロード
        _modules = collect_modules(MODULE_PATTERNS)
        load_modules(_modules)
```

---

## 5. 段階的な実装計画

### Step 1: 最小限の addon.py

```python
# addon.py（最小実装）
from . import core
from . import menus
from . import infra
from . import ui

MODULES = [core, menus, infra, ui]

def register_modules():
    for mod in MODULES:
        if hasattr(mod, "register"):
            mod.register()

def unregister_modules():
    for mod in reversed(MODULES):
        if hasattr(mod, "unregister"):
            mod.unregister()
```

### Step 2: パターンベースの収集

glob パターンでモジュールを自動収集。

### Step 3: 依存解析とソート

import 文を解析してトポロジカルソート。

### Step 4: reload 対応

`use_reload` パターンの導入。

---

## 6. PME 本体との対比

| 機能 | PME mini | PME 本体 |
|------|----------|---------|
| モジュール収集 | シンプルなリスト | glob パターン |
| 依存解析 | なし（手動順序） | AST 解析 + トポロジカルソート |
| reload | 基本対応 | `use_reload` パターン |
| デバッグ | print | `DBG_*` フラグ + 構造化ログ |

PME mini では**シンプルさを優先**し、必要になったら機能を追加する。
