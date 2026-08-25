#!/usr/bin/env python3
"""E1: 生データ → 対応付きデータセット（`protocol/exclusion_rules.md` の実装）.

本実験のデータが存在しない時点で書く（`pre_pilot_decisions.md` 決定4）。
後から書くと、分析方法を結果に合わせて選べてしまう。

## このスクリプトが守る規則（すべて事前登録済み）

- **除外できるのはインフラ起因のみ**（§1）。モデルの失敗・受入テスト不合格は
  アームの成績なので**除外しない**（§2）。
- **対応は spec × rep のペア単位**（§3）。片アームが無効ならペアごと落とす。
- **停止条件**: インフラ起因の再実行率が 20% を超えたら停止を宣告する（§3）。
- **モデルID / CLI バージョンが2種類以上**なら混ぜて集計せず停止を宣告する（§4）。
- **事後の外れ値除外はしない**（§5）。全数を出す。

出力: `analysis/e1_dataset.json`
    pairs: [{spec, rep, cost_B, cost_C, wall_B, wall_C, accepted_B, accepted_C, ...}]
    stop_conditions: 停止条件に触れたかどうか（触れたら E2 は判定を出さない）
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# インフラ起因（＝除外して再実行してよい）と判定する status / notes の手掛かり。
# exclusion_rules.md §1 に列挙されたものだけを機械判定に落とす。
INFRA_MARKERS = (
    "NoModelCallError",      # 空振り・部分実行（provider 枯渇を含む）
    "session limit",
    "rate limit",
    "quota",
    "timeout",
    "5xx",
    "Connection",
    "backend failed",
)
RERUN_STOP_RATIO = 0.20      # §3 停止条件


def is_infra_failure(status: str, notes: str) -> bool:
    if status == "completed":
        return False
    blob = f"{status} {notes}".lower()
    return any(m.lower() in blob for m in INFRA_MARKERS)


def load_ledger(label: str) -> list[dict]:
    path = ROOT / f"run_ledger_{label}.csv"
    if not path.exists():
        print(f"[ERROR] 台帳が無い: {path}", file=sys.stderr)
        raise SystemExit(1)
    return [r for r in csv.DictReader(path.open(encoding="utf-8"))
            if r.get("status") != "dry_run"]


def load_calls(root: Path, spec: str, arm: str, rep: int) -> list[dict]:
    p = root / spec / arm / f"rep{rep}" / "calls.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "main"
    runs_root = ROOT / "runs" / label
    ledger = load_ledger(label)

    # --- 各 run の最終状態（同一 run_id の最後の行を採る。再実行は追記される）---
    final: dict[str, dict] = {}
    attempts: dict[str, int] = defaultdict(int)
    infra_failures = 0
    for row in ledger:
        rid = row.get("run_id", "")
        attempts[rid] += 1
        if is_infra_failure(row.get("status", ""), row.get("notes", "") or ""):
            infra_failures += 1
        final[rid] = row

    total_runs = len(final)
    rerun_ratio = (infra_failures / total_runs) if total_runs else 0.0

    # --- 交絡の統制（§4）: モデル / CLI が単一か ---
    models, clis = set(), set()
    for rid, row in final.items():
        if row.get("status") != "completed":
            continue
        spec, arm, rep = row["spec"], row["arm"], int(row["rep"])
        for c in load_calls(runs_root, spec, arm, rep):
            if c.get("model"):
                models.add(c["model"])
            if c.get("cli_version"):
                clis.add(c["cli_version"])

    stop: list[str] = []
    if rerun_ratio > RERUN_STOP_RATIO:
        stop.append(f"インフラ起因の再実行率 {rerun_ratio:.1%} が停止閾値 "
                    f"{RERUN_STOP_RATIO:.0%} を超えた（exclusion_rules §3）")
    if len(models) > 1:
        stop.append(f"モデルIDが複数ある: {sorted(models)}（§4。混ぜて集計しない）")
    if len(clis) > 1:
        stop.append(f"CLIバージョンが複数ある: {sorted(clis)}（§4。層別または再実行）")

    # --- ペア構築（§3: 片アーム無効ならペアごと落とす）---
    by_pair: dict[tuple[str, int], dict[str, dict]] = defaultdict(dict)
    for rid, row in final.items():
        by_pair[(row["spec"], int(row["rep"]))][row["arm"]] = row

    pairs, dropped = [], []
    for (spec, rep), arms in sorted(by_pair.items()):
        b, c = arms.get("B"), arms.get("C")
        if not b or not c:
            dropped.append({"spec": spec, "rep": rep,
                            "reason": "片アームが存在しない（欠測）"})
            continue
        if b.get("status") != "completed" or c.get("status") != "completed":
            bad = [a for a, r in (("B", b), ("C", c)) if r.get("status") != "completed"]
            dropped.append({"spec": spec, "rep": rep,
                            "reason": f"アーム{','.join(bad)} が completed でない"})
            continue
        rows_b = load_calls(runs_root, spec, arm="B", rep=rep)
        rows_c = load_calls(runs_root, spec, arm="C", rep=rep)
        if not rows_b or not rows_c:
            dropped.append({"spec": spec, "rep": rep,
                            "reason": "calls.jsonl が無い（計装欠損・§1）"})
            continue
        pairs.append({
            "spec": spec, "rep": rep,
            "cost_B": float(b["cost_usd"] or 0), "cost_C": float(c["cost_usd"] or 0),
            "wall_B": float(b["wall_s"] or 0), "wall_C": float(c["wall_s"] or 0),
            "accepted_B": int(b["accepted"] or 0), "accepted_C": int(c["accepted"] or 0),
            "tasks_B": len(rows_b), "tasks_C": len(rows_c),
            "resumed_C": sum(1 for r in rows_c if r.get("resumed")),
            "attempts_B": attempts.get(f"{spec}_B_rep{rep}", 1),
            "attempts_C": attempts.get(f"{spec}_C_rep{rep}", 1),
        })

    out = {
        "label": label,
        "generated_by": "analysis/e1_aggregate.py",
        "n_pairs": len(pairs),
        "n_runs_seen": total_runs,
        "infra_failures": infra_failures,
        "rerun_ratio": round(rerun_ratio, 4),
        "models": sorted(models),
        "cli_versions": sorted(clis),
        "stop_conditions": stop,
        "dropped_pairs": dropped,
        "pairs": pairs,
        "note": "事後の外れ値除外はしていない（exclusion_rules §5）。全数を出している。",
    }
    dest = ROOT / "analysis" / f"e1_dataset_{label}.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"=== E1 ({label}) ===")
    print(f"有効ペア {len(pairs)} / 落としたペア {len(dropped)} / run 総数 {total_runs}")
    print(f"インフラ起因 {infra_failures} 件（再実行率 {rerun_ratio:.1%}）")
    print(f"model={sorted(models)}  cli={sorted(clis)}")
    if dropped:
        print("\n落としたペア:")
        for d in dropped:
            print(f"  {d['spec']} rep{d['rep']}: {d['reason']}")
    if stop:
        print("\n*** 停止条件に該当 ***")
        for s in stop:
            print(f"  - {s}")
        print("  → E2 は判定を出さない。原因を解消し Amendment Log に記録すること。")
    print(f"\n→ {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
