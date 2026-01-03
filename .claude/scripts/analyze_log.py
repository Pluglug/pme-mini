#!/usr/bin/env python3
# .claude/scripts/analyze_log.py - NDJSON ログ解析スクリプト
#
# 使い方:
#   python analyze_log.py                    # 最新セッションを解析
#   python analyze_log.py --category deps    # 特定カテゴリのみ
#   python analyze_log.py --level error      # エラーのみ
#   python analyze_log.py --json             # JSON 形式で出力
#   python analyze_log.py --stats            # 統計情報のみ
#   python analyze_log.py --list             # セッション一覧

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


# ログディレクトリ
SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR.parent / "logs"


@dataclass
class LogEntry:
    """パースされたログエントリ"""

    session_id: str
    timestamp: int
    level: str
    category: str
    message: str
    data: dict[str, Any]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LogEntry:
        return cls(
            session_id=d.get("session_id", ""),
            timestamp=d.get("timestamp", 0),
            level=d.get("level", "info"),
            category=d.get("category", "general"),
            message=d.get("message", ""),
            data={
                k: v
                for k, v in d.items()
                if k not in ("session_id", "timestamp", "level", "category", "message")
            },
        )

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000)

    def format_human(self) -> str:
        """人間可読形式"""
        time_str = self.datetime.strftime("%H:%M:%S.%f")[:-3]
        level_icon = {"debug": "🔍", "info": "ℹ️", "warn": "⚠️", "error": "❌"}.get(self.level, "•")
        data_str = ""
        if self.data:
            data_str = " " + " ".join(f"{k}={v}" for k, v in self.data.items())
        return f"{time_str} {level_icon} [{self.category}] {self.message}{data_str}"


def find_latest_log() -> Path | None:
    """最新のログファイルを探す"""
    # latest.ndjson シンボリックリンクを確認
    latest_link = LOG_DIR / "latest.ndjson"
    if latest_link.exists():
        if latest_link.is_symlink():
            return latest_link.resolve()
        return latest_link

    # latest.txt（シンボリックリンク代替）を確認
    latest_txt = LOG_DIR / "latest.txt"
    if latest_txt.exists():
        target_name = latest_txt.read_text().strip()
        target_path = LOG_DIR / target_name
        if target_path.exists():
            return target_path

    # なければ最新の .ndjson ファイルを探す
    log_files = sorted(
        [f for f in LOG_DIR.glob("*.ndjson") if f.name != "latest.ndjson"],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return log_files[0] if log_files else None


def list_sessions() -> list[dict[str, Any]]:
    """セッション一覧を取得"""
    sessions = []
    for log_file in sorted(LOG_DIR.glob("*.ndjson"), reverse=True):
        if log_file.name == "latest.ndjson":
            continue
        try:
            size = log_file.stat().st_size
            with log_file.open(encoding="utf-8") as fp:
                line_count = sum(1 for _ in fp)
            sessions.append(
                {
                    "file": log_file.name,
                    "size": size,
                    "entries": line_count,
                    "modified": datetime.fromtimestamp(log_file.stat().st_mtime),
                },
            )
        except Exception:
            pass
    return sessions


def parse_log(path: Path) -> Iterator[LogEntry]:
    """NDJSON ログファイルをパース"""
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                yield LogEntry.from_dict(data)
            except json.JSONDecodeError:
                continue


def filter_entries(
    entries: Iterator[LogEntry],
    category: str | None = None,
    level: str | None = None,
    search: str | None = None,
) -> Iterator[LogEntry]:
    """エントリをフィルタリング"""
    level_order = {"debug": 0, "info": 1, "warn": 2, "error": 3}
    min_level = level_order.get(level, 0) if level else 0

    for entry in entries:
        if category and entry.category != category:
            continue
        if level_order.get(entry.level, 0) < min_level:
            continue
        if search and search.lower() not in entry.message.lower():
            continue
        yield entry


def compute_stats(entries: list[LogEntry]) -> dict[str, Any]:
    """統計情報を計算"""
    if not entries:
        return {"total": 0}

    by_level = Counter(e.level for e in entries)
    by_category = Counter(e.category for e in entries)

    # 時間範囲
    timestamps = [e.timestamp for e in entries]
    duration_ms = max(timestamps) - min(timestamps)

    # パフォーマンスログの集計
    profile_entries = [e for e in entries if e.category == "profile"]
    slow_operations = []
    if profile_entries:
        for e in profile_entries:
            if "duration_ms" in e.data and e.data["duration_ms"] > 10:
                slow_operations.append(
                    {
                        "scope": e.data.get("scope", "unknown"),
                        "duration_ms": e.data["duration_ms"],
                    },
                )
        slow_operations.sort(key=lambda x: x["duration_ms"], reverse=True)

    # 依存関係違反
    violations = []
    for e in entries:
        if e.category == "deps" and e.data.get("violations"):
            violations.extend(e.data["violations"])

    return {
        "total": len(entries),
        "by_level": dict(by_level),
        "by_category": dict(by_category),
        "duration_ms": duration_ms,
        "slow_operations": slow_operations[:10],  # Top 10
        "violations": list(set(violations)),
    }


def print_human(entries: list[LogEntry], stats: dict[str, Any]) -> None:
    """人間可読形式で出力"""
    # ヘッダー
    print(f"\n{'='*60}")
    print(f"📋 Log Analysis - {stats['total']} entries")
    print(f"{'='*60}\n")

    # 統計サマリー
    if stats["total"] > 0:
        print("📊 Summary:")
        print(f"   Levels:     {stats['by_level']}")
        print(f"   Categories: {stats['by_category']}")
        if stats["duration_ms"] > 0:
            print(f"   Duration:   {stats['duration_ms']:.0f}ms")
        print()

    # 違反があれば表示
    if stats.get("violations"):
        print("⚠️ Layer Violations:")
        for v in stats["violations"]:
            print(f"   - {v}")
        print()

    # 遅い処理があれば表示
    if stats.get("slow_operations"):
        print("🐢 Slow Operations (>10ms):")
        for op in stats["slow_operations"][:5]:
            print(f"   - {op['scope']}: {op['duration_ms']:.1f}ms")
        print()

    # エントリ一覧
    print("📝 Entries:")
    for entry in entries:
        print(f"   {entry.format_human()}")


def print_json(entries: list[LogEntry], stats: dict[str, Any]) -> None:
    """JSON 形式で出力"""
    output = {
        "stats": stats,
        "entries": [
            {
                "timestamp": e.timestamp,
                "level": e.level,
                "category": e.category,
                "message": e.message,
                **e.data,
            }
            for e in entries
        ],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False, default=str))


def main():
    parser = argparse.ArgumentParser(description="PME mini ログ解析ツール")
    parser.add_argument("file", nargs="?", help="解析するログファイル（省略時は latest）")
    parser.add_argument("-c", "--category", help="カテゴリでフィルタ")
    parser.add_argument(
        "-l",
        "--level",
        choices=["debug", "info", "warn", "error"],
        help="最小ログレベル",
    )
    parser.add_argument("-s", "--search", help="メッセージ検索")
    parser.add_argument("--json", action="store_true", help="JSON 形式で出力")
    parser.add_argument("--stats", action="store_true", help="統計情報のみ")
    parser.add_argument("--list", action="store_true", help="セッション一覧")
    parser.add_argument("--tail", type=int, default=0, help="最新 N 件のみ")

    args = parser.parse_args()

    # セッション一覧
    if args.list:
        sessions = list_sessions()
        if not sessions:
            print("No log sessions found.")
            return
        print(f"\n{'='*60}")
        print("📁 Log Sessions")
        print(f"{'='*60}\n")
        for s in sessions:
            print(f"   {s['file']}")
            print(f"      Entries: {s['entries']:,}  Size: {s['size']:,} bytes")
            print(f"      Modified: {s['modified']}")
            print()
        return

    # ログファイル決定
    if args.file:
        log_path = Path(args.file)
        if not log_path.exists():
            log_path = LOG_DIR / args.file
    else:
        log_path = find_latest_log()

    if not log_path or not log_path.exists():
        print("No log file found. Run PME mini first to generate logs.")
        sys.exit(1)

    print(f"Analyzing: {log_path.name}")

    # パースとフィルタリング
    entries = list(
        filter_entries(
            parse_log(log_path),
            category=args.category,
            level=args.level,
            search=args.search,
        ),
    )

    # tail オプション
    if args.tail > 0:
        entries = entries[-args.tail :]

    # 統計計算
    stats = compute_stats(entries)

    # 出力
    if args.json:
        print_json(entries, stats)
    elif args.stats:
        print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))
    else:
        print_human(entries, stats)


if __name__ == "__main__":
    main()
