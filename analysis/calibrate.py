#!/usr/bin/env python3
"""R1: 較正データから r̂（仕様ごとの費用比 Cost_C/Cost_B の予測）を算出する.

§3.8.4 の要件を満たすための設計:
  - **パイロットの C/B 比を使わない。** 入力は較正キャンペーン（アームB のみ）だけ。
  - **r̂ を手入力しない。** 本スクリプトが較正データから計算し JSON へ書く。
  - 較正データ・本コード・出力を同時にコミットしてから本実験を開始する。

出力: analysis/model_predictions.json（H4(b) の判定に使う）

## モデル（sec3 §3.3〜3.5, v0.3）

アームB（毎タスク fresh）:
    Cost_B(j) ≈ α_r·S·K_j + e_j + W_j
アームC（レーン継続）: 継承 H を運ぶ代わりに再探索 e を払わない
    Cost_C(j) ≈ α_r·S·K'_j + (ρ·α_w + (K'_j − ρ)·α_r)·H_j + W_j

ここで K'_j は継続時のターン数（再探索が消えるぶん K_j より小さい）。
較正では B 側から S・K_j・e_j・W_j を推定し、C 側の K'_j と H_j はモデルで予測する。

## 操作的定義（§3.8.3。恣意性は Limitations に明記する）

  E（再探索）: **最初に編集系ツール（Write/Edit/NotebookEdit）を呼ぶまで**のターン群
  W（本来の作業）: それ以降のターン群
  S: そのランで観測された1ターンあたり context の最小値（CLI 固定文脈の下界）

## 単価

すべて USD。実測 cost_usd と整合するよう、単価は `PRICES` に明示して持つ。
"""
from __future__ import annotations

import json
import os
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EDIT_TOOLS = {"Write", "Edit", "NotebookEdit", "MultiEdit"}

# 単価（USD / 1M tokens）。model 名で引く。較正データに現れたモデルだけ必要。
PRICES = {
    "claude-sonnet-5": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0, "cache_read": 0.10, "cache_write": 1.25},
}
ALPHA_R = 0.1     # cache_read / input
ALPHA_W = 1.25    # cache_write / input


def completed_run_ids(ledger: Path) -> set[str] | None:
    """台帳で `completed` になった run_id の集合。台帳が無ければ None（全採用）。

    中断ラン（部分実行・provider 枯渇）の calls.jsonl は途中まで書かれているため、
    これを較正に混ぜると E/W/K が過小に出る。`exclusion_rules.md` の方針に従い、
    **台帳で completed のものだけ**を較正に使う。
    """
    if not ledger.exists():
        return None
    import csv

    ok: set[str] = set()
    with ledger.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") == "completed":
                ok.add(row.get("run_id", ""))
    return ok


def load_runs(root: Path, allowed: set[str] | None = None) -> list[dict]:
    runs = []
    for calls in sorted(root.rglob("calls.jsonl")):
        rows = [json.loads(l) for l in calls.open(encoding="utf-8") if l.strip()]
        if not rows:
            continue
        spec, arm, rep = rows[0].get("spec"), rows[0].get("arm"), rows[0].get("rep")
        run_id = f"{spec}_{arm}_rep{rep}"
        if allowed is not None and run_id not in allowed:
            print(f"  [除外] {run_id}: 台帳が completed でない", file=sys.stderr)
            continue
        runs.append({"spec": spec, "arm": arm, "rep": rep, "rows": rows})
    return runs


def split_e_w(turns: list[dict]) -> tuple[list[dict], list[dict]]:
    """§3.8.3 の操作的定義で E（再探索）と W（本来の作業）へ分ける。"""
    for i, t in enumerate(turns):
        if any(name in EDIT_TOOLS for name in (t.get("tools") or [])):
            return turns[:i], turns[i:]
    return turns, []  # 編集が一度も無ければ全部 E 扱い（要 Limitations 記載）


def calibrate_task(row: dict) -> dict | None:
    """1タスク（＝CLI 1呼び出し）の B 側実測から E / W / S / K を推定する。"""
    turns = row.get("turns") or []
    if not turns:
        return None
    contexts = [t.get("context_tokens") or 0 for t in turns]
    s_hat = min(contexts) if contexts else 0
    e_turns, w_turns = split_e_w(turns)
    # 各ターンの「S を超える分」＝そのターンが運んだ固有の文脈
    def own(ts: list[dict]) -> int:
        return sum(max(0, (t.get("context_tokens") or 0) - s_hat) for t in ts)
    return {
        "task_id": row.get("task_id") or "",
        "K": row.get("num_turns") or len(turns),
        "K_E": len(e_turns),
        "K_W": len(w_turns),
        "S_hat": s_hat,
        "E_tokens": own(e_turns),          # 再探索で運んだ文脈量
        "W_tokens": own(w_turns),
        "peak_context": max(contexts),
        "cost_usd": row.get("cost_usd") or 0.0,
        "model": row.get("model"),
        "edit_tool_seen": bool(w_turns),
    }


def predict_ratio(tasks: list[dict], lanes: dict[str, list[str]]) -> dict:
    """仕様全体の r̂ = Cost_C / Cost_B を、B 側の較正値から予測する。

    レーン内で2件目以降のタスクだけが継続の対象になる。継続タスクは
      - 再探索 E を払わない（K が K_E 分だけ減る）
      - 代わりに継承 H を毎ターン α_r で運ぶ（初回のみ ρ の書き直し）
    H の予測は「直前タスクの peak_context」を用いる（実測で単調増加を確認済み）。
    """
    by_id = {t["task_id"]: t for t in tasks}
    price = PRICES.get(tasks[0].get("model") or "", PRICES["claude-sonnet-5"])
    unit_in = price["input"] / 1e6

    def cost_b(t: dict) -> float:
        # 実測 cost をそのまま使う（B 側は較正データで直接観測できる）
        return t["cost_usd"]

    def cost_c(t: dict, h_prev: int | None, rho: int) -> float:
        if h_prev is None:
            return t["cost_usd"]           # レーン先頭は B と同じ
        # 再探索ぶんの文脈が消え、代わりに H を毎ターン運ぶ
        saved = t["E_tokens"] * ALPHA_R * unit_in
        k_c = max(1, t["K"] - t["K_E"])
        carried = (rho * ALPHA_W + (k_c - rho) * ALPHA_R) * h_prev * unit_in
        return t["cost_usd"] - saved + carried

    total_b = total_c = 0.0
    detail = []
    for lane_id, task_ids in lanes.items():
        h_prev = None
        for pos, tid in enumerate(task_ids):
            t = by_id.get(tid)
            if t is None:
                continue
            rho = 1 if pos > 0 else 0     # 初回 resume で書き直しが起きる側に倒す
            cb, cc = cost_b(t), cost_c(t, h_prev, rho)
            total_b += cb
            total_c += cc
            detail.append({"task_id": tid, "lane": lane_id, "pos": pos,
                           "H_prev": h_prev, "rho": rho,
                           "cost_B": round(cb, 4), "cost_C_pred": round(cc, 4)})
            h_prev = t["peak_context"]
    return {"r_hat": round(total_c / total_b, 4) if total_b else None,
            "total_B": round(total_b, 4), "total_C_pred": round(total_c, 4),
            "tasks": detail}


def main() -> int:
    calib_root = ROOT / "runs" / (sys.argv[1] if len(sys.argv) > 1 else "calib")
    specs_path = ROOT / "benchmarks" / "specs.json"
    if not calib_root.exists():
        print(f"[ERROR] 較正データが無い: {calib_root}", file=sys.stderr)
        return 1

    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    specs = specs["specs"] if isinstance(specs, dict) else specs
    lanes_by_spec = {}
    for s in specs:
        plan = json.loads(Path(s["plan"]).read_text(encoding="utf-8"))
        sys.path.insert(0, os.environ.get(
            "PAPER_HARNESS_REPO",
            str(Path(__file__).resolve().parents[2] / "旧agent-framework")))
        from fwcore.lanes import build_lanes  # noqa: E402

        class _T:
            def __init__(self, d):
                self.task_id = d.get("task_id")
                a = d.get("artifacts") or {}
                self._w = set(a.get("creates") or []) | set(a.get("modifies") or [])

        ts = [_T(d) for d in plan["tasks"]]
        la = build_lanes(ts, lambda t: t._w)
        lanes_by_spec[s["spec_id"]] = {lid: list(tids)
                                       for lid, tids in la.tasks_of.items()}

    out = {"generated_by": "analysis/calibrate.py",
           "calibration_source": str(calib_root.relative_to(ROOT)),
           "note": "アームB のみから較正した。パイロットの C/B 比は入力に含まない（§3.8.4）。",
           "operational_definition": {
               "E": "最初に編集系ツール（Write/Edit/NotebookEdit/MultiEdit）を呼ぶまでのターン群",
               "W": "それ以降のターン群",
               "S": "そのランで観測された1ターンあたり context の最小値",
               "rho": "レーン2件目以降は 1（初回 resume で書き直しが起きる側に倒す）"},
           "alpha_r": ALPHA_R, "alpha_w": ALPHA_W,
           "specs": {}}

    label = calib_root.name
    allowed = completed_run_ids(ROOT / f"run_ledger_{label}.csv")
    out["completed_runs_only"] = allowed is not None
    for run in load_runs(calib_root, allowed):
        if run["arm"] != "B":
            continue
        tasks = [c for c in (calibrate_task(r) for r in run["rows"]) if c]
        if not tasks:
            continue
        lanes = lanes_by_spec.get(run["spec"], {})
        pred = predict_ratio(tasks, lanes)
        out["specs"][run["spec"]] = {
            "lanes": lanes,
            "calibration": tasks,
            "prediction": pred,
        }

    dest = ROOT / "analysis" / "model_predictions.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'spec':<18}{'tasks':>6}{'lanes':>7}{'r_hat':>9}{'E比':>8}")
    for spec, d in sorted(out["specs"].items()):
        ts = d["calibration"]
        e_share = (sum(t["E_tokens"] for t in ts) /
                   max(1, sum(t["E_tokens"] + t["W_tokens"] for t in ts)))
        print(f"{spec:<18}{len(ts):>6}{len(d['lanes']):>7}"
              f"{d['prediction']['r_hat'] or 0:>9.3f}{e_share:>8.1%}")
    rs = [d["prediction"]["r_hat"] for d in out["specs"].values()
          if d["prediction"]["r_hat"]]
    if rs:
        print(f"\nr̂ 中央値 {st.median(rs):.3f}  範囲 {min(rs):.3f}〜{max(rs):.3f}")
        print("  r̂ < 1 なら C が安いと予測、> 1 なら高いと予測")
    print(f"\n→ {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
