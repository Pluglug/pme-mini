# pme.py - 外部向けファサード API
#
# 外部スクリプトや他アドオンからの公式エントリポイント。
# 内部実装を隠蔽し、安定した API を提供する。
#
# 使用例:
#   from pme_mini import pme
#   pme.execute("bpy.ops.mesh.primitive_cube_add()")
#   menu = pme.find_menu("My Pie Menu")
#
# 設計方針:
#   - 最小限の API から始める
#   - 内部構造の変更に強い（ファサードで吸収）
#   - 型ヒントで使い方を明確に

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# =============================================================================
# Stability Levels（安定性レベル）
# =============================================================================
#
# Stable      — 互換性を維持。外部からの依存を想定
# Experimental — 変更の可能性あり。フィードバック次第
# Internal    — 外部からの利用は非推奨。予告なく変更


# =============================================================================
# Executor API (Experimental)
# =============================================================================


@dataclass
class ExecuteResult:
    """コード実行の結果。

    Stability: Experimental
    """

    success: bool
    error_message: str | None = None


def execute(code: str, *, extra_globals: dict[str, Any] | None = None) -> ExecuteResult:
    """任意の Python コードを実行する。

    標準名前空間（C, D, bpy など）は自動的に提供される。
    extra_globals で追加の変数を渡すことができる。

    Args:
        code: 実行する Python コード
        extra_globals: 追加のグローバル変数

    Returns:
        ExecuteResult: 実行結果

    Example:
        result = pme.execute("bpy.ops.mesh.primitive_cube_add()")
        if not result.success:
            print(f"Error: {result.error_message}")

    Stability: Experimental
    """
    import bpy

    # 標準名前空間を構築
    globals_dict = {
        "bpy": bpy,
        "C": bpy.context,
        "D": bpy.data,
    }

    # 追加のグローバル変数をマージ
    if extra_globals:
        globals_dict.update(extra_globals)

    try:
        exec(code, globals_dict)
        return ExecuteResult(success=True)
    except Exception as e:
        return ExecuteResult(success=False, error_message=str(e))


def evaluate(expr: str, *, extra_globals: dict[str, Any] | None = None) -> Any:
    """式を評価して結果を返す。

    評価に失敗した場合は例外を投げる。
    poll 用途で try-except が必要な場合は呼び出し側で処理する。

    Args:
        expr: 評価する式
        extra_globals: 追加のグローバル変数

    Returns:
        評価結果

    Raises:
        SyntaxError: 構文エラー
        NameError: 未定義の変数参照
        その他の例外

    Example:
        is_edit_mode = pme.evaluate("C.mode == 'EDIT_MESH'")

    Stability: Experimental
    """
    import bpy

    globals_dict = {
        "bpy": bpy,
        "C": bpy.context,
        "D": bpy.data,
    }

    if extra_globals:
        globals_dict.update(extra_globals)

    return eval(expr, globals_dict)


# =============================================================================
# Menu Integration API (Experimental)
# =============================================================================


@dataclass
class MenuHandle:
    """メニューの読み取り専用ハンドル。

    内部データを直接公開せず、必要な情報のみ提供する。

    Stability: Experimental
    """

    name: str
    type_id: str
    enabled: bool = True

    # 将来の拡張候補
    # hotkey: str | None = None
    # tag: str | None = None


def find_menu(name: str) -> MenuHandle | None:
    """名前でメニューを検索する。

    Args:
        name: メニュー名

    Returns:
        MenuHandle または None（見つからない場合）

    Example:
        menu = pme.find_menu("My Pie Menu")
        if menu:
            print(f"Found: {menu.name} ({menu.type_id})")

    Stability: Experimental
    """
    from .infra.registry import MenuRegistry

    schema = MenuRegistry.get_menu(name)
    if schema is None:
        return None

    return MenuHandle(
        name=schema.name,
        type_id=schema.type_id(),
        enabled=getattr(schema, "enabled", True),
    )


def list_menus() -> list[MenuHandle]:
    """全メニューのリストを取得する。

    Returns:
        MenuHandle のリスト

    Example:
        for menu in pme.list_menus():
            print(f"{menu.name}: {menu.type_id}")

    Stability: Experimental
    """
    from .infra.registry import MenuRegistry

    return [
        MenuHandle(
            name=schema.name,
            type_id=schema.type_id(),
            enabled=getattr(schema, "enabled", True),
        )
        for schema in MenuRegistry.list_menus()
    ]


def invoke_menu(menu_or_name: MenuHandle | str) -> bool:
    """メニューを呼び出す（表示する）。

    Args:
        menu_or_name: MenuHandle またはメニュー名

    Returns:
        成功したら True、失敗したら False

    Example:
        pme.invoke_menu("My Pie Menu")

    Stability: Experimental
    """
    name = menu_or_name.name if isinstance(menu_or_name, MenuHandle) else menu_or_name

    # TODO: 実際の Pie Menu 呼び出し実装
    # 現時点ではプレースホルダー
    print(f"[PME mini] invoke_menu: {name} (not implemented yet)")
    return False


# =============================================================================
# Poll Helpers (Experimental)
# =============================================================================


class polls:
    """よくある poll 条件のプリセット。

    これらは文字列定数であり、evaluate() と組み合わせて使う。

    Example:
        if pme.evaluate(pme.polls.MESH_EDIT):
            # Edit Mode のときだけ実行
            ...

    Stability: Experimental
    """

    MESH_EDIT = "C.mode == 'EDIT_MESH'"
    OBJECT_MODE = "C.mode == 'OBJECT'"
    SCULPT_MODE = "C.mode == 'SCULPT'"
    HAS_ACTIVE_OBJECT = "C.active_object is not None"
    HAS_SELECTED = "len(C.selected_objects) > 0"


# =============================================================================
# 内部用（Internal）
# =============================================================================
# 以下は外部からの利用を想定していない。予告なく変更される。


def _get_registry():
    """Internal: Registry への直接アクセス（デバッグ用）"""
    from .infra.registry import MenuRegistry

    return MenuRegistry


# =============================================================================
# モジュール初期化
# =============================================================================


def register():
    """アドオン登録時に呼ばれる"""
    pass


def unregister():
    """アドオン登録解除時に呼ばれる"""
    pass
