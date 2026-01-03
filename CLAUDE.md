# CLAUDE.md

PME mini の開発ガイド。Claude Code がこのプロジェクトで作業する際の指針。

---

## 1. プロジェクト概要

**PME mini** は、PME2 の設計実験のための最小プロトタイプ。

### 目的

1. **設計パターンの検証** — Protocol, dataclass, Registry パターンを実際に動かして学ぶ
2. **PME2 への知見還元** — ここで得た設計を PME 本体に適用する
3. **学習のための実験場** — 失敗しても本体に影響しない

### PME 本体との関係

| プロジェクト | 目的 | 状態 |
|-------------|------|------|
| `pie_menu_editor/` (PME2) | 本番アドオン | 開発中 |
| `pme_mini/` | 設計実験 | **実験中** |

**注意**: pme_mini のコードを PME2 に直接コピーしない。設計の知見を還元する。

---

## 2. アーキテクチャ

### レイヤ構造

```
ui      (3) ← Blender UI パネル、描画
infra   (2) ← Blender API 連携、オペレーター、Registry
menus   (1) ← メニュータイプの具体的実装 (Behavior, View)
core    (0) ← Blender 非依存 (Protocol, Schema)
```

### 依存方向

- **許可**: 上位 → 下位（ui → infra → menus → core）
- **禁止**: 下位 → 上位（core は他に依存しない）

### 核となる設計

#### Protocol による緩い契約

```python
# 継承なし、必要なメソッドを実装するだけで契約を満たす
@runtime_checkable
class MenuSchema(Protocol):
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict) -> "MenuSchema": ...
```

#### Schema / Behavior / View 分離

| 責務 | クラス例 | 役割 |
|------|---------|------|
| Schema | `PieMenuSchema` | データ構造（設定値、シリアライズ） |
| Behavior | `PieMenuBehavior` | 振る舞いルール（固定スロット数など） |
| View | `PieMenuView` | UI 描画（設定パネル、メニュー本体） |

#### Registry パターン

```python
# メニュータイプの登録
MenuRegistry.register_type(PieMenuSchema, PieMenuBehavior(), PieMenuView())

# メニューインスタンスの作成
menu = MenuRegistry.create_menu("pie", "My Menu")
```

#### 外部 API ファサード（pme.py）

```python
# 外部スクリプトからの利用
from pme_mini import pme

# コード実行
result = pme.execute("bpy.ops.mesh.primitive_cube_add()")

# 式の評価
is_edit = pme.evaluate("C.mode == 'EDIT_MESH'")

# メニュー検索
menu = pme.find_menu("My Pie Menu")
```

---

## 3. 開発方針

### やること

- Protocol と dataclass を活用した型安全な設計
- 小さな機能を段階的に追加
- 日本語コメント（学習目的のため）

### やらないこと

- 本番品質のエラーハンドリング
- 複雑なエッジケース対応
- パフォーマンス最適化

### コードスタイル

```python
# コメントは日本語
class PieMenuSchema:
    """
    Pie Menu のスキーマ。

    PME の PMItem + "pm" タイプのプロパティに相当。
    """
    name: str = "New Pie Menu"
    radius: int = -1  # -1 = デフォルト値を使用
```

---

## 4. 現在のファイル構成

```
pme_mini/
├── __init__.py           # アドオンエントリ
├── CLAUDE.md             # 本ファイル
├── pme.py                # 外部 API ファサード
├── .claude/
│   └── rules/
│       ├── architecture.md  # レイヤ構造、依存ルール
│       ├── development.md   # 開発フロー、コーディング規約
│       ├── loader.md        # addon.py ローダー設計
│       └── api.md           # pme.py API 設計
├── core/
│   ├── __init__.py       # エクスポート
│   ├── protocols.py      # Protocol 定義
│   └── schemas.py        # dataclass スキーマ
├── menus/
│   ├── __init__.py
│   └── pie_menu.py       # PieMenuBehavior, PieMenuView
├── infra/
│   ├── __init__.py       # オペレーター登録
│   └── registry.py       # MenuRegistry
└── ui/
    ├── __init__.py
    └── panels.py         # サイドバーパネル
```

---

## 5. 次のマイルストーン

### Phase 1: 基盤整備 ⏳

- [ ] `addon.py` ローダーの実装
- [ ] 設定の永続化（JSON 保存/読み込み）
- [ ] 基本的な Pie Menu 呼び出し

### Phase 2: エディタ機能

- [ ] アイテム編集 UI
- [ ] ホットキー設定
- [ ] プレビュー機能

### Phase 3: PME2 への知見整理

- [ ] 学んだパターンの文書化
- [ ] PME2 適用計画の作成

---

## 6. 参照

- `pie_menu_editor/CLAUDE.md` — PME2 本体のガイド
- `pie_menu_editor/.claude/rules/` — PME2 の詳細ルール
- `pie_menu_editor/docs/core-layer/` — core 層設計ドキュメント
