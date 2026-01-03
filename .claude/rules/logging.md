# rules/logging.md

PME mini のセッションベース構造化ロガー設計。

---

## 1. 設計方針

### Claude Code 時代の要件

| 要件 | 解決策 |
|------|--------|
| AI がパースしやすい | NDJSON 形式（1行1JSON） |
| セッションごとに分離 | タイムスタンプ付きファイル名 |
| 軽量で読みやすい | 最大10セッション、自動ローテーション |
| 分析しやすい | ロガーごとのスキーマ定義 + 解析スクリプト |
| Blender 実行中に切替可能 | フラグベースの動的制御 |

### loguru を使わない理由

- Blender アドオンとしてのパッケージング問題
- 依存関係の最小化
- Python 標準の logging で十分

---

## 2. アーキテクチャ

### ファイル構成

```
pme_mini/
├── infra/
│   └── logger.py           # ロガー実装
└── .claude/
    ├── logs/
    │   ├── latest.ndjson   # 最新セッションへのシンボリックリンク
    │   ├── 2026-01-03_20-30-00.ndjson
    │   └── ...             # 最大10セッション
    └── scripts/
        └── analyze_log.py  # 解析スクリプト
```

### クラス構成

```
LoggerRegistry (singleton)
├── session_id: str
├── log_path: Path
├── _loggers: dict[str, StructuredLogger]
└── configure() / get_logger() / rotate_sessions()

StructuredLogger
├── name: str
├── schema: LogSchema
├── enabled: bool
└── log() / debug() / info() / warn() / error()

LogSchema (dataclass)
├── category: str
├── fields: dict[str, type]
└── validate() / to_dict()
```

---

## 3. データスキーマ

### 基本フィールド（全ログ共通）

```python
@dataclass
class BaseLogEntry:
    session_id: str      # セッション識別子
    timestamp: int       # Unix ms
    level: str           # debug/info/warn/error
    category: str        # ロガーカテゴリ
    message: str         # 人間可読メッセージ
```

### カテゴリ別スキーマ

```python
# 依存関係ログ
@dataclass
class DepsLogEntry(BaseLogEntry):
    module: str          # モジュール名
    imports: list[str]   # インポート先
    layer: int           # レイヤ番号
    violations: list[str] # 違反リスト

# パフォーマンスログ
@dataclass
class ProfileLogEntry(BaseLogEntry):
    scope: str           # 計測対象
    duration_ms: float   # 所要時間
    memory_delta: int    # メモリ変化（バイト）

# レジストリログ
@dataclass
class RegistryLogEntry(BaseLogEntry):
    action: str          # register/unregister/create
    menu_type: str       # pie/regular/dialog
    menu_name: str       # メニュー名
```

### NDJSON 出力例

```json
{"session_id":"s_20260103_203000","timestamp":1735912200000,"level":"info","category":"deps","message":"Module loaded","module":"core.schemas","imports":["dataclasses"],"layer":0,"violations":[]}
{"session_id":"s_20260103_203000","timestamp":1735912200050,"level":"debug","category":"profile","message":"Schema init","scope":"PieMenuSchema.__init__","duration_ms":0.5,"memory_delta":1024}
{"session_id":"s_20260103_203000","timestamp":1735912200100,"level":"info","category":"registry","message":"Menu registered","action":"register","menu_type":"pie","menu_name":"My Pie"}
```

---

## 4. ランタイム切り替え

### フラグベース制御

```python
# Blender 実行中に切り替え可能
LoggerRegistry.set_enabled("deps", True)
LoggerRegistry.set_enabled("profile", False)
LoggerRegistry.set_level("registry", "debug")
```

### PropertyGroup 連携（将来）

```python
class LoggerPrefs(bpy.types.PropertyGroup):
    enable_deps: BoolProperty(
        name="Dependencies",
        default=False,
        update=lambda s, c: LoggerRegistry.set_enabled("deps", s.enable_deps)
    )
    enable_profile: BoolProperty(
        name="Profile",
        default=False,
        update=lambda s, c: LoggerRegistry.set_enabled("profile", s.enable_profile)
    )
```

---

## 5. 解析スクリプト

### 基本的な使い方

```bash
# 最新セッションを解析
python .claude/scripts/analyze_log.py

# 特定カテゴリのみ
python .claude/scripts/analyze_log.py --category deps

# エラーのみ
python .claude/scripts/analyze_log.py --level error

# JSON 出力
python .claude/scripts/analyze_log.py --json
```

### jq での解析

```bash
# 依存関係の違反のみ抽出
cat .claude/logs/latest.ndjson | jq 'select(.category=="deps" and .violations!=[])'

# パフォーマンスの遅い処理
cat .claude/logs/latest.ndjson | jq 'select(.category=="profile" and .duration_ms>100)'

# エラー一覧
cat .claude/logs/latest.ndjson | jq 'select(.level=="error") | {message, category}'
```

---

## 6. 使用例

### 基本的なログ出力

```python
from pme_mini.infra.logger import get_logger

# カテゴリ別ロガー取得
deps_log = get_logger("deps")
profile_log = get_logger("profile")
registry_log = get_logger("registry")

# ログ出力
deps_log.info("Module loaded", module="core.schemas", imports=["dataclasses"], layer=0)
profile_log.debug("Schema init", scope="PieMenuSchema.__init__", duration_ms=0.5)
registry_log.info("Menu registered", action="register", menu_type="pie", menu_name="My Pie")
```

### コンテキストマネージャ

```python
from pme_mini.infra.logger import profile_scope

with profile_scope("heavy_operation"):
    # 時間計測したい処理
    do_something_expensive()
# → 自動的に duration_ms が記録される
```

---

## 7. セッション管理

### 自動ローテーション

```python
# 起動時に自動実行
LoggerRegistry.rotate_sessions(max_sessions=10)
# → 古いセッションファイルを削除
# → latest.ndjson を更新
```

### セッション ID 形式

```
s_YYYYMMDD_HHMMSS
例: s_20260103_203000
```

---

## 8. 実装優先度

| 優先度 | 機能 | 理由 |
|--------|------|------|
| 🔴 高 | 基本ログ出力 | 開発に必須 |
| 🔴 高 | NDJSON 形式 | AI 解析に必須 |
| 🟡 中 | セッションローテーション | ファイル肥大化防止 |
| 🟡 中 | 解析スクリプト | 効率的なデバッグ |
| 🟢 低 | PropertyGroup 連携 | UI からの制御 |

---

## 9. 参照

- `pie_menu_editor/infra/debug.py` — PME2 の NDJSON ログ実装
- `modular_renamer/utils/logging.py` — Python logging ラッパー
- NDJSON 仕様: https://ndjson.org/
