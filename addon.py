# addon.py - アドオンライフサイクル管理
#
# PME2 の addon.py を簡略化したローダー。
# 小規模プロトタイプ向けに最適化。
#
# 参考:
#   - pie_menu_editor/addon.py (フル機能版)
#   - modular_renamer/__init__.py (use_reload パターン)

from __future__ import annotations

import ast
import importlib
import inspect
import os
import pkgutil
import re
import sys
import traceback
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import bpy

if TYPE_CHECKING:
    pass

# ===========================================================================
# アドオン情報
# ===========================================================================

ADDON_ID = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
ADDON_PATH = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
VERSION: tuple[int, int, int] | None = None

# モジュール管理
MODULE_NAMES: list[str] = []
MODULE_PATTERNS: list[re.Pattern] = []
_class_cache: list[type] | None = None

# デバッグフラグ
DBG_LOADER = os.environ.get("PME_MINI_DBG_LOADER", "0") == "1"


# ===========================================================================
# ファサード関数
# ===========================================================================


def get_prefs():
    """アドオン設定を取得（将来用）"""
    uprefs = bpy.context.preferences
    addon = uprefs.addons.get(ADDON_ID)
    if addon:
        return addon.preferences
    return None


# ===========================================================================
# ローダー API
# ===========================================================================


def init_addon(
    module_patterns: list[str],
    use_reload: bool = False,
    version: tuple[int, int, int] | None = None,
) -> None:
    """
    アドオンモジュールの初期化。

    Args:
        module_patterns: ロード対象のモジュールパターン (例: ["core.*", "ui.*"])
        use_reload: リロードモードかどうか
        version: アドオンバージョン

    Example:
        init_addon(
            module_patterns=["core.*", "menus.*", "infra.*", "ui.*"],
            use_reload=use_reload,
        )
    """
    global VERSION, _class_cache

    if version:
        VERSION = version

    _class_cache = None

    # パターンをコンパイル
    MODULE_PATTERNS[:] = [
        re.compile(f"^{ADDON_ID}\\.{p.replace('*', '.*')}$") for p in module_patterns
    ]

    _log("init", f"Initializing {ADDON_ID}")
    _log("init", f"Patterns: {[p.pattern for p in MODULE_PATTERNS]}")

    # モジュール収集
    module_names = list(_collect_module_names())
    _log("init", f"Found {len(module_names)} modules")

    # モジュールロード
    load_errors = 0
    for mod_name in module_names:
        try:
            if use_reload and mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])
                _log("reload", mod_name)
            else:
                importlib.import_module(mod_name)
                _log("import", mod_name)
        except Exception as e:
            load_errors += 1
            _log("error", f"Failed to load {mod_name}: {e}")
            traceback.print_exc()

    if load_errors:
        _log("warn", f"{load_errors} modules failed to load")

    # 依存関係解決とソート
    sorted_modules = _sort_modules(module_names)
    MODULE_NAMES[:] = sorted_modules

    _log("init", f"Load order: {len(MODULE_NAMES)} modules")
    if DBG_LOADER:
        for i, m in enumerate(MODULE_NAMES):
            print(f"  {i+1:2}. {_short_name(m)}")


def register_modules() -> None:
    """
    全モジュールを Blender に登録。

    1. クラスを依存順でソート
    2. クラスを登録
    3. 各モジュールの register() を呼び出し
    """
    if bpy.app.background:
        return

    _log("register", "Starting registration...")

    # クラス登録
    classes = _get_classes()
    class_count = 0
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
            class_count += 1
        except Exception as e:
            _log("error", f"Class {cls.__name__}: {e}")

    _log("register", f"Registered {class_count} classes")

    # モジュール初期化
    init_count = 0
    for mod_name in MODULE_NAMES:
        mod = sys.modules.get(mod_name)
        if mod and hasattr(mod, "register"):
            try:
                mod.register()
                init_count += 1
            except Exception as e:
                _log("error", f"Module {_short_name(mod_name)}: {e}")
                traceback.print_exc()

    _log("register", f"Initialized {init_count} modules")


def unregister_modules() -> None:
    """
    全モジュールを Blender から登録解除。

    逆順で:
    1. 各モジュールの unregister() を呼び出し
    2. クラスを登録解除
    """
    if bpy.app.background:
        return

    _log("unregister", "Starting unregistration...")

    # モジュール終了処理（逆順）
    uninit_count = 0
    for mod_name in reversed(MODULE_NAMES):
        mod = sys.modules.get(mod_name)
        if mod and hasattr(mod, "unregister"):
            try:
                mod.unregister()
                uninit_count += 1
            except Exception as e:
                _log("error", f"Module {_short_name(mod_name)}: {e}")

    _log("unregister", f"Uninitialized {uninit_count} modules")

    # クラス登録解除（逆順）
    classes = _get_classes()
    class_count = 0
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
            class_count += 1
        except Exception as e:
            _log("error", f"Class {cls.__name__}: {e}")

    _log("unregister", f"Unregistered {class_count} classes")


# ===========================================================================
# 内部ヘルパー
# ===========================================================================


def _collect_module_names() -> list[str]:
    """パターンにマッチするモジュール名を収集"""

    def is_matched(name: str) -> bool:
        return any(p.match(name) for p in MODULE_PATTERNS)

    def scan(path: str, package: str) -> list[str]:
        modules = []
        try:
            entries = list(pkgutil.iter_modules([path]))
        except Exception:
            return modules

        for _, name, is_pkg in entries:
            if name.startswith("_"):
                continue

            full_name = f"{package}.{name}"
            if is_pkg:
                modules.extend(scan(os.path.join(path, name), full_name))
            if is_matched(full_name):
                modules.append(full_name)

        return modules

    return scan(ADDON_PATH, ADDON_ID)


def _sort_modules(module_names: list[str]) -> list[str]:
    """依存関係に基づいてモジュールをソート"""
    graph = _analyze_dependencies(module_names)

    # フィルタリング
    filtered = {
        n: {d for d in deps if d in module_names} for n, deps in graph.items() if n in module_names
    }

    # 全モジュールがグラフに含まれるようにする
    for mod in module_names:
        if mod not in filtered:
            filtered[mod] = set()

    try:
        return _topological_sort(filtered)
    except ValueError as e:
        _log("warn", f"Topological sort failed: {e}")
        # フォールバック: レイヤ優先度でソート
        return _priority_sort(module_names)


def _analyze_dependencies(module_names: list[str]) -> dict[str, set[str]]:
    """モジュール間の依存関係を解析"""
    import_graph = _analyze_imports(module_names)

    # import_graph は {module: {dependencies}} 形式
    # これを {dependency: {dependents}} に変換
    graph: dict[str, set[str]] = defaultdict(set)
    for mod, deps in import_graph.items():
        for dep in deps:
            graph[dep].add(mod)

    # PropertyGroup 依存も追加
    pdtype = bpy.props._PropertyDeferred
    for mod_name in module_names:
        mod = sys.modules.get(mod_name)
        if not mod:
            continue

        for _, cls in inspect.getmembers(mod, _is_bpy_class):
            for prop in getattr(cls, "__annotations__", {}).values():
                if isinstance(prop, pdtype) and prop.function in (
                    bpy.props.PointerProperty,
                    bpy.props.CollectionProperty,
                ):
                    dep_cls = prop.keywords.get("type")
                    if dep_cls and dep_cls.__module__ in module_names:
                        if dep_cls.__module__ != mod_name:
                            graph[dep_cls.__module__].add(mod_name)

    return graph


def _analyze_imports(module_names: list[str]) -> dict[str, set[str]]:
    """import 文を解析して依存関係を抽出"""
    graph: dict[str, set[str]] = defaultdict(set)

    class ImportVisitor(ast.NodeVisitor):
        def __init__(self, mod_name: str):
            self.mod_name = mod_name
            self.in_type_checking = False
            self.in_function = False

        def visit_If(self, node: ast.If):
            if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                old = self.in_type_checking
                self.in_type_checking = True
                self.generic_visit(node)
                self.in_type_checking = old
            else:
                self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef):
            old = self.in_function
            self.in_function = True
            self.generic_visit(node)
            self.in_function = old

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self.visit_FunctionDef(node)  # type: ignore

        def visit_ImportFrom(self, node: ast.ImportFrom):
            if self.in_type_checking or self.in_function:
                return

            if not node.module:
                return

            # 相対インポートを解決
            if node.level > 0:
                parts = self.mod_name.split(".")
                if node.level <= len(parts):
                    base = ".".join(parts[: -node.level])
                    module_path = f"{base}.{node.module}" if node.module else base
                else:
                    return
            else:
                module_path = node.module

            if module_path.startswith(ADDON_ID) and module_path in module_names:
                graph[self.mod_name].add(module_path)

    for mod_name in module_names:
        mod = sys.modules.get(mod_name)
        if not mod or not hasattr(mod, "__file__") or not mod.__file__:
            continue

        try:
            with open(mod.__file__, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=mod.__file__)
            visitor = ImportVisitor(mod_name)
            visitor.visit(tree)
        except Exception:
            pass

    return graph


def _topological_sort(graph: dict[str, set[str]]) -> list[str]:
    """Kahn のアルゴリズムでトポロジカルソート"""
    in_degree: dict[str, int] = defaultdict(int)
    for node in graph:
        for neighbor in graph[node]:
            in_degree[neighbor] += 1

    queue = [n for n in graph if in_degree[n] == 0]
    result = []

    while queue:
        node = queue.pop(0)
        result.append(node)

        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(graph):
        remaining = set(graph.keys()) - set(result)
        raise ValueError(f"Circular dependency: {remaining}")

    return result


def _priority_sort(module_names: list[str]) -> list[str]:
    """レイヤ優先度に基づくフォールバックソート"""

    def priority(mod: str) -> int:
        short = _short_name(mod)
        if short.startswith("core"):
            return 0
        elif short.startswith("menus"):
            return 1
        elif short.startswith("infra"):
            return 2
        elif short.startswith("ui"):
            return 3
        else:
            return 10

    return sorted(module_names, key=priority)


def _get_classes() -> list[type]:
    """登録可能なクラスを依存順で取得"""
    global _class_cache

    if _class_cache is not None:
        return _class_cache

    pdtype = bpy.props._PropertyDeferred
    class_deps: dict[type, set[type]] = defaultdict(set)
    all_classes: list[type] = []

    for mod_name in MODULE_NAMES:
        mod = sys.modules.get(mod_name)
        if not mod:
            continue

        for _, cls in inspect.getmembers(mod, _is_bpy_class):
            deps: set[type] = set()
            for prop in getattr(cls, "__annotations__", {}).values():
                if isinstance(prop, pdtype):
                    pfunc = getattr(prop, "function", None) or prop[0]
                    if pfunc in (bpy.props.PointerProperty, bpy.props.CollectionProperty):
                        dep_cls = prop.keywords.get("type")
                        if dep_cls and dep_cls.__module__.startswith(ADDON_ID):
                            deps.add(dep_cls)
            class_deps[cls] = deps
            all_classes.append(cls)

    # DFS でソート
    ordered: list[type] = []
    visited: set[type] = set()
    stack: list[type] = []

    def visit(cls: type):
        if cls in stack:
            cycle = " -> ".join(c.__name__ for c in stack)
            raise ValueError(f"Circular class dependency: {cycle}")
        if cls not in visited:
            stack.append(cls)
            visited.add(cls)
            for dep in class_deps.get(cls, []):
                visit(dep)
            stack.pop()
            ordered.append(cls)

    for cls in all_classes:
        if cls not in visited:
            visit(cls)

    _class_cache = ordered
    return ordered


def _is_bpy_class(obj: Any) -> bool:
    """Blender に登録可能なクラスかどうか"""
    return (
        inspect.isclass(obj)
        and issubclass(obj, bpy.types.bpy_struct)
        and obj.__base__ is not bpy.types.bpy_struct
        and obj.__module__.startswith(ADDON_ID)
    )


def _short_name(mod_name: str) -> str:
    """モジュール名を短縮"""
    prefix = f"{ADDON_ID}."
    return mod_name[len(prefix) :] if mod_name.startswith(prefix) else mod_name


def _log(category: str, message: str) -> None:
    """シンプルなログ出力"""
    if DBG_LOADER or category in ("error", "warn"):
        print(f"[{ADDON_ID}] {category}: {message}")
