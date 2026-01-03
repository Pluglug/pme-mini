# infra/logger.py - セッションベース構造化ロガー
#
# Claude Code 時代のための NDJSON ロガー。
# 各ロガーインスタンスがスキーマを持ち、解析スクリプトとセットで使う。

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# ===========================================================================
# 定数
# ===========================================================================

# ログディレクトリ（.claude/logs/）
_ADDON_DIR = Path(__file__).parent.parent
_LOG_DIR = _ADDON_DIR / ".claude" / "logs"
_MAX_SESSIONS = 10

# セッション ID（起動時に生成）
_SESSION_ID: str = ""
_LOG_PATH: Path | None = None


# ===========================================================================
# スキーマ定義
# ===========================================================================


@dataclass
class LogSchema:
    """ロガーごとのデータスキーマ。

    各カテゴリが持つべきフィールドを定義。
    解析スクリプトがこのスキーマを参照して型安全に処理できる。
    """

    category: str
    fields: dict[str, type] = field(default_factory=dict)
    description: str = ""

    def validate(self, data: dict[str, Any]) -> bool:
        """データがスキーマに適合するか検証"""
        for name, expected_type in self.fields.items():
            if name in data:
                if not isinstance(data[name], expected_type):
                    return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """スキーマをシリアライズ（解析スクリプト用）"""
        return {
            "category": self.category,
            "fields": {k: v.__name__ for k, v in self.fields.items()},
            "description": self.description,
        }


# ===========================================================================
# 組み込みスキーマ
# ===========================================================================

SCHEMA_DEPS = LogSchema(
    category="deps",
    fields={
        "module": str,
        "imports": list,
        "layer": int,
        "violations": list,
    },
    description="依存関係とレイヤ違反のログ",
)

SCHEMA_PROFILE = LogSchema(
    category="profile",
    fields={
        "scope": str,
        "duration_ms": float,
        "memory_delta": int,
    },
    description="パフォーマンス計測ログ",
)

SCHEMA_REGISTRY = LogSchema(
    category="registry",
    fields={
        "action": str,
        "menu_type": str,
        "menu_name": str,
    },
    description="メニュー登録・操作ログ",
)

SCHEMA_GENERAL = LogSchema(
    category="general",
    fields={},
    description="汎用ログ",
)


# ===========================================================================
# ロガー本体
# ===========================================================================


class StructuredLogger:
    """カテゴリ別の構造化ロガー。

    スキーマを持ち、NDJSON 形式で出力する。
    ランタイムで有効/無効を切り替え可能。
    """

    def __init__(self, name: str, schema: LogSchema):
        self.name = name
        self.schema = schema
        self.enabled = True
        self.level = "debug"  # debug/info/warn/error
        self._level_order = {"debug": 0, "info": 1, "warn": 2, "error": 3}

    def _should_log(self, level: str) -> bool:
        """ログ出力すべきか判定"""
        if not self.enabled:
            return False
        return self._level_order.get(level, 0) >= self._level_order.get(self.level, 0)

    def _emit(self, level: str, message: str, **data: Any) -> None:
        """NDJSON にログを追記"""
        if not self._should_log(level):
            return

        if _LOG_PATH is None:
            return  # 初期化前

        # スキーマ検証（デバッグ時のみ）
        if not self.schema.validate(data):
            # 警告を出すが、ログは出力する
            pass

        entry = {
            "session_id": _SESSION_ID,
            "timestamp": int(time.time() * 1000),
            "level": level,
            "category": self.schema.category,
            "message": message,
            **data,
        }

        try:
            with _LOG_PATH.open("a", encoding="utf-8") as fp:
                json.dump(entry, fp, ensure_ascii=False, default=str)
                fp.write("\n")
        except Exception:
            # ログ出力失敗は無視（無限ループ防止）
            pass

    def debug(self, message: str, **data: Any) -> None:
        """デバッグログ"""
        self._emit("debug", message, **data)

    def info(self, message: str, **data: Any) -> None:
        """情報ログ"""
        self._emit("info", message, **data)

    def warn(self, message: str, **data: Any) -> None:
        """警告ログ"""
        self._emit("warn", message, **data)

    def error(self, message: str, **data: Any) -> None:
        """エラーログ"""
        self._emit("error", message, **data)

    def log(self, level: str, message: str, **data: Any) -> None:
        """汎用ログ"""
        self._emit(level, message, **data)


# ===========================================================================
# レジストリ（シングルトン）
# ===========================================================================


class LoggerRegistry:
    """ロガー管理のシングルトン。

    セッション管理、ロガー取得、ランタイム設定を担当。
    """

    _loggers: dict[str, StructuredLogger] = {}
    _initialized = False
    _schemas: dict[str, LogSchema] = {}

    @classmethod
    def init(cls) -> None:
        """ロガーシステムの初期化。

        セッション ID の生成、ログファイルの作成、
        古いセッションのローテーションを行う。
        """
        global _SESSION_ID, _LOG_PATH

        if cls._initialized:
            return

        # セッション ID 生成
        now = datetime.now()
        _SESSION_ID = f"s_{now.strftime('%Y%m%d_%H%M%S')}"

        # ログディレクトリ作成
        _LOG_DIR.mkdir(parents=True, exist_ok=True)

        # ログファイルパス
        _LOG_PATH = _LOG_DIR / f"{now.strftime('%Y-%m-%d_%H-%M-%S')}.ndjson"

        # latest シンボリックリンク更新
        latest_link = _LOG_DIR / "latest.ndjson"
        try:
            if latest_link.exists() or latest_link.is_symlink():
                latest_link.unlink()
            # Windows ではシンボリックリンクに管理者権限が必要な場合がある
            # その場合はファイルコピーで代用
            try:
                latest_link.symlink_to(_LOG_PATH.name)
            except OSError:
                # シンボリックリンク失敗時はテキストファイルでパスを記録
                latest_link.with_suffix(".txt").write_text(str(_LOG_PATH.name))
        except Exception:
            pass

        # 古いセッションをローテーション
        cls._rotate_sessions()

        # 組み込みスキーマを登録
        cls._schemas = {
            "deps": SCHEMA_DEPS,
            "profile": SCHEMA_PROFILE,
            "registry": SCHEMA_REGISTRY,
            "general": SCHEMA_GENERAL,
        }

        cls._initialized = True

        # 初期化ログ
        general = cls.get_logger("general")
        general.info("Logger initialized", session_id=_SESSION_ID, log_path=str(_LOG_PATH))

    @classmethod
    def _rotate_sessions(cls) -> None:
        """古いセッションファイルを削除"""
        try:
            log_files = sorted(
                [f for f in _LOG_DIR.glob("*.ndjson") if f.name != "latest.ndjson"],
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            # 最新 N 件以外を削除
            for old_file in log_files[_MAX_SESSIONS:]:
                old_file.unlink()
        except Exception:
            pass

    @classmethod
    def get_logger(cls, category: str) -> StructuredLogger:
        """カテゴリ別ロガーを取得。

        未初期化の場合は自動初期化する。
        """
        if not cls._initialized:
            cls.init()

        if category not in cls._loggers:
            schema = cls._schemas.get(category, SCHEMA_GENERAL)
            cls._loggers[category] = StructuredLogger(category, schema)

        return cls._loggers[category]

    @classmethod
    def register_schema(cls, schema: LogSchema) -> None:
        """カスタムスキーマを登録"""
        cls._schemas[schema.category] = schema

    @classmethod
    def set_enabled(cls, category: str, enabled: bool) -> None:
        """ロガーの有効/無効を切り替え"""
        if category in cls._loggers:
            cls._loggers[category].enabled = enabled

    @classmethod
    def set_level(cls, category: str, level: str) -> None:
        """ロガーのログレベルを設定"""
        if category in cls._loggers:
            cls._loggers[category].level = level

    @classmethod
    def set_all_enabled(cls, enabled: bool) -> None:
        """全ロガーの有効/無効を切り替え"""
        for logger in cls._loggers.values():
            logger.enabled = enabled

    @classmethod
    def export_schemas(cls) -> dict[str, Any]:
        """全スキーマをエクスポート（解析スクリプト用）"""
        return {name: schema.to_dict() for name, schema in cls._schemas.items()}

    @classmethod
    def get_log_path(cls) -> Path | None:
        """現在のログファイルパスを取得"""
        return _LOG_PATH

    @classmethod
    def get_session_id(cls) -> str:
        """現在のセッション ID を取得"""
        return _SESSION_ID


# ===========================================================================
# 便利関数
# ===========================================================================


def get_logger(category: str) -> StructuredLogger:
    """ロガー取得のショートカット"""
    return LoggerRegistry.get_logger(category)


@contextmanager
def profile_scope(scope: str, logger: StructuredLogger | None = None):
    """パフォーマンス計測用コンテキストマネージャ。

    使用例:
        with profile_scope("heavy_operation"):
            do_something_expensive()
    """
    if logger is None:
        logger = get_logger("profile")

    start_time = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Completed: {scope}", scope=scope, duration_ms=duration_ms, memory_delta=0)


# ===========================================================================
# モジュールレベル初期化
# ===========================================================================


def init_logger() -> None:
    """ロガーシステムを明示的に初期化"""
    LoggerRegistry.init()


def shutdown_logger() -> None:
    """ロガーシステムのシャットダウン"""
    LoggerRegistry._initialized = False
    LoggerRegistry._loggers.clear()
