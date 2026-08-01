#!/usr/bin/env python3
"""B1: 形状クラスごとの plan.json と specs.json を生成し、レーン構成を検証する.

既存の受入テスト付きカード（square-media @ d4449a0）を SHAPES.md の写像に従って
plan へ組み立てる。**新規タスクは作らない。**

生成後、fwcore.lanes.build_lanes で実際のレーン構成を計算し、
意図した形状（W=2レーン×1 / N=1レーン×2 / M=3レーン）になっているかを検証する。
意図と実装がずれていたら、この時点で落とす。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = str(Path.home() / "project" / "square-media")
BASE_COMMIT = "d4449a0"   # 4カードすべてが「テスト有・実装無」で揃う唯一の点（SHAPES.md）

# --- タスク定義（受入テストの契約から起こした中立な記述） -------------------
# 注: 既存カードの本文には、ローカルモデルの弱点回避のための指示
#     （old_text アンカーの指定など）が混ざっている。本実験は別モデルで走るため、
#     そうしたモデル固有の回避策は除き、受入テストが要求する内容だけを書く。

T1310 = dict(
    task_id="T-1310",
    title="ウィンドウタイトルの日本語化",
    creates=[], modifies=["src/ui/app.py"], deps=[],
    description=(
        "src/ui/app.py のネイティブウィンドウタイトルを日本語化する。"
        "モジュールレベル定数 WINDOW_TITLE を定義し（値は日本語を含み、製品名 "
        "'Square Media' を残すこと）、self.title(\"Square Media\") を "
        "self.title(WINDOW_TITLE) に置き換える。記事タイトルの翻訳は範囲外。"
        "受入テスト tests/nightly/test_window_title.py は変更しないこと。"
    ),
)

T1311 = dict(
    task_id="T-1311",
    title="reader_states テーブルの migration",
    creates=[], modifies=["src/db.py"], deps=[],
    description=(
        "src/db.py に migrate_reader_states(db_path=DB_PATH) を追加する。"
        "reader_states テーブル（列: item_id TEXT PRIMARY KEY, is_read INTEGER NOT NULL "
        "DEFAULT 0, is_saved INTEGER NOT NULL DEFAULT 0, is_skipped INTEGER NOT NULL "
        "DEFAULT 0, user_rating INTEGER, updated_at TEXT）を CREATE TABLE IF NOT EXISTS "
        "で作成し、冪等であること。既存テーブルには触れない。UIは変更しない。"
        "受入テスト tests/nightly/test_reader_states_migration.py は変更しないこと。"
    ),
)

T1312 = dict(
    task_id="T-1312",
    title="reader state の読み書きAPI",
    creates=[], modifies=["src/db.py"], deps=["T-1311"],
    description=(
        "src/db.py に reader state の読み書きAPIを追加する（migrate_reader_states が前提）。"
        "(1) set_reader_state(item_id, db_path=DB_PATH, is_read=None, is_saved=None, "
        "is_skipped=None, user_rating=None): None でない引数だけを更新する upsert。"
        "省略した項目は以前の値を保持。updated_at に現在時刻のISO文字列を保存。"
        "(2) get_reader_state(item_id, db_path=DB_PATH): 該当行を dict で返す。無ければ None。"
        "受入テスト tests/nightly/test_reader_states_api.py は変更しないこと。"
    ),
)

T1320 = dict(
    task_id="T-1320",
    title="可視テキスト抽出の純関数",
    creates=["src/security/html_text.py"], modifies=[], deps=[],
    description=(
        "新規ファイル src/security/html_text.py に純関数 to_visible_text(text) を実装する。"
        "HTMLまたはプレーンテキストを受け取り、人間に見える本文だけを返す。要件: "
        "(1) 数式やコード中の裸の '<'（例 'i<n'）で本文を切り捨てない。"
        "(2) 実在するHTMLタグ（<p> <video> <div> 等）は除去する。"
        "(3) <script> と <style> の中身は本文に含めない。"
        "(4) HTMLエンティティ（&amp; 等）はアンエスケープする。"
        "(5) 入力が None や空文字なら空文字を返す。"
        "ネットワーク・ファイルI/Oは行わない。標準ライブラリのみ。"
        "受入テスト tests/test_html_text.py は変更しないこと。"
    ),
)

# --- 系列2: square-media-spec/sprint_17-1 由来 ------------------------------
# Sprint 17 は ai-runtime の ModelGateway 契約に依存して着手不能だったため、
# 依存の無い前半を sprint_17-1 として切り出した（square-media-spec 9413161）。
# 受入テストは square-media 3be3676 で「テスト有・実装無」に固定してある。
# 系列1（d4449a0 の nightly カード）とは別リポ状態・別ファイル群なので、
# 形状の効果が特定の仕様に固有でないことの確認に使える。
BASE_COMMIT_S17 = "3be3676"

T17101 = dict(
    task_id="T-17101",
    title="summary の provider メタデータ migration",
    creates=[], modifies=["src/db.py"], deps=[],
    description=(
        "src/db.py に migrate_summary_provenance(db_path=DB_PATH) を追加する。"
        "既存の summaries テーブルへ provider TEXT / model TEXT / usage_id TEXT の "
        "3列を追加する。既存の _ensure_column と同じ方針で、存在しない列だけを "
        "ALTER TABLE で追加し、冪等であること。既存行のデータを壊さないこと"
        "（新列は NULL のままでよい）。他のテーブルには触れない。UIは変更しない。"
        "受入テスト tests/sprint17_1/test_summary_provenance_migration.py は"
        "変更しないこと。"
    ),
)

T17102 = dict(
    task_id="T-17102",
    title="summary provenance の読み書きAPI",
    creates=[], modifies=["src/db.py"], deps=["T-17101"],
    description=(
        "src/db.py に summary provenance の読み書きAPIを追加する"
        "（migrate_summary_provenance が前提）。"
        "(1) set_summary_provenance(item_id, provider=None, model=None, "
        "usage_id=None, db_path=DB_PATH): None でない引数だけを更新する。"
        "省略した項目は以前の値を保持すること。"
        "(2) get_summary_provenance(item_id, db_path=DB_PATH): "
        "provider / model / usage_id を持つ dict を返す。"
        "該当する summaries 行が無ければ None を返す。"
        "Runtime の利用台帳を複製せず、参照用IDだけを保存する。"
        "受入テスト tests/sprint17_1/test_summary_provenance_api.py は"
        "変更しないこと。"
    ),
)

T17103 = dict(
    task_id="T-17103",
    title="安全処理とプロバイダ実行の分離",
    creates=[], modifies=["src/llm/safe_llm_runner.py"], deps=[],
    description=(
        "src/llm/safe_llm_runner.py の run_safe_llm() から、injection 検知と "
        "safe prompt 組み立て（STEP 1-2）を、CLI 実行（STEP 3以降）から切り離す。"
        "(1) PreparedCall dataclass を追加する: stdin_text: str, "
        "detection: DetectionResult, injection_detected: bool。"
        "(2) build_safe_prompt(request: LLMRequest) -> PreparedCall | None を追加する。"
        "firewall が call_llm=False と判定したら None を返し、プロバイダを呼ばない。"
        "この関数の中でサブプロセスを起動しないこと。"
        "(3) run_safe_llm() は build_safe_prompt() を使うよう書き換える。ただし"
        "戻り値 LLMResult と、command が list[str] でない場合に TypeError を送出する"
        "既存契約は変えないこと。"
        "SafePrompt という名前の型を新たに定義しないこと"
        "（src/security/prompt_firewall.py の同名の型をそのまま使う）。"
        "受入テスト tests/sprint17_1/test_safe_prompt_split.py は変更しないこと。"
    ),
)

PYTEST = ["python3", "-m", "pytest", "-q"]

S17 = "tests/sprint17_1/"

SPECS = [
    dict(spec_id="n_db_chain", shape="N", tasks=[T1311, T1312],
         verify=PYTEST + ["tests/nightly/test_reader_states_migration.py",
                          "tests/nightly/test_reader_states_api.py"],
         expect_lanes={"lane_count": 1, "max_tasks_per_lane": 2}),
    dict(spec_id="w_two_files", shape="W", tasks=[T1310, T1320],
         verify=PYTEST + ["tests/nightly/test_window_title.py",
                          "tests/test_html_text.py"],
         expect_lanes={"lane_count": 2, "max_tasks_per_lane": 1}),
    dict(spec_id="m_mixed", shape="M", tasks=[T1310, T1311, T1312, T1320],
         verify=PYTEST + ["tests/nightly/test_window_title.py",
                          "tests/nightly/test_reader_states_migration.py",
                          "tests/nightly/test_reader_states_api.py",
                          "tests/test_html_text.py"],
         expect_lanes={"lane_count": 3, "max_tasks_per_lane": 2}),

    # --- 系列2: sprint_17-1 ---
    dict(spec_id="s17_n_db_chain", shape="N", tasks=[T17101, T17102],
         commit=BASE_COMMIT_S17,
         verify=PYTEST + [S17 + "test_summary_provenance_migration.py",
                          S17 + "test_summary_provenance_api.py"],
         expect_lanes={"lane_count": 1, "max_tasks_per_lane": 2}),
    dict(spec_id="s17_w_two_files", shape="W", tasks=[T17101, T17103],
         commit=BASE_COMMIT_S17,
         verify=PYTEST + [S17 + "test_summary_provenance_migration.py",
                          S17 + "test_safe_prompt_split.py"],
         expect_lanes={"lane_count": 2, "max_tasks_per_lane": 1}),
    dict(spec_id="s17_m_mixed", shape="M", tasks=[T17101, T17102, T17103],
         commit=BASE_COMMIT_S17,
         verify=PYTEST + [S17],
         expect_lanes={"lane_count": 2, "max_tasks_per_lane": 2}),
]


def to_task(t: dict) -> dict:
    return {
        "task_id": t["task_id"],
        "feature_id": "F-1",
        "title": t["title"],
        "type": "implementation",
        "description": t["description"],
        "dependencies": t["deps"],
        "artifacts": {"creates": t["creates"], "modifies": t["modifies"], "reads": []},
        "test_hints": [],
        "estimated_effort_h": 1.0,
        "prototype_required": False,
        "status": "pending",
    }


def to_plan(spec: dict) -> dict:
    tasks = [to_task(t) for t in spec["tasks"]]
    return {
        "sprint_id": "sprint_1",
        "generated_at": "2026-08-01T00:00:00+09:00",
        "tasks": tasks,
        "dependency_graph": {t["task_id"]: t["dependencies"] for t in tasks},
        "execution_batches": [],
        "metadata": {"errors": [], "shape": spec["shape"], "spec_id": spec["spec_id"]},
    }


def verify_lanes(spec: dict, plan: dict) -> tuple[bool, str]:
    """意図した形状に実際になるかを fwcore.lanes で検証する。"""
    sys.path.insert(0, str(Path.home() / "project" / "旧agent-framework"))
    from fwcore.lanes import build_lanes  # noqa: E402

    class T:
        def __init__(self, d):
            self.task_id = d["task_id"]
            self._w = set(d["artifacts"]["creates"]) | set(d["artifacts"]["modifies"])

    tasks = [T(t) for t in plan["tasks"]]
    la = build_lanes(tasks, lambda t: t._w)
    exp = spec["expect_lanes"]
    got_count = la.lane_count
    got_max = max(len(v) for v in la.tasks_of.values())
    ok = (got_count == exp["lane_count"] and got_max == exp["max_tasks_per_lane"])
    return ok, (f"lanes={got_count}(期待{exp['lane_count']}) "
                f"max/lane={got_max}(期待{exp['max_tasks_per_lane']})  {la.summary()}")


def main() -> int:
    plans_dir = HERE / "plans"
    plans_dir.mkdir(exist_ok=True)
    out_specs = []
    all_ok = True

    print(f"{'spec':<14}{'shape':<7}{'tasks':<7}検証")
    for spec in SPECS:
        plan = to_plan(spec)
        p = plans_dir / f"{spec['spec_id']}.plan.json"
        p.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        ok, detail = verify_lanes(spec, plan)
        all_ok &= ok
        mark = "OK " if ok else "NG "
        print(f"{spec['spec_id']:<14}{spec['shape']:<7}{len(plan['tasks']):<7}{mark}{detail}")
        out_specs.append({
            "spec_id": spec["spec_id"], "shape": spec["shape"],
            "repo": REPO, "commit": spec.get("commit", BASE_COMMIT),
            "plan": str(p), "verify": spec["verify"],
            "tasks_per_lane": spec["expect_lanes"]["max_tasks_per_lane"],
        })

    (HERE / "specs.json").write_text(
        json.dumps({"specs": out_specs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nspecs.json: {HERE / 'specs.json'}")
    if not all_ok:
        print("\n[FAIL] 意図した形状にならない spec がある。写像を見直すこと。", file=sys.stderr)
        return 1
    print("[OK] 全 spec が意図したレーン構成になった")
    return 0


if __name__ == "__main__":
    sys.exit(main())
