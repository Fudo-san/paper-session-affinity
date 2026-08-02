#!/usr/bin/env python3
"""特定 run の中身を確認する。異常値がインフラ起因か観測かを見分けるため。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def show(label: str, spec: str, arm: str, rep: int) -> None:
    d = ROOT / "runs" / label / spec / arm / f"rep{rep}"
    rj = d / "run.json"
    print(f"=== {spec} {arm} rep{rep} ===")
    if not rj.exists():
        print("  run.json なし")
        return
    r = json.loads(rj.read_text(encoding="utf-8"))
    u = r.get("usage_actual") or {}
    print(f"  accepted={r.get('accepted')}  wall={r.get('wall_s')}s  "
          f"cost=${u.get('cost_usd', 0):.4f}")
    print(f"  cache_read={u.get('cache_read_tokens', 0):,}  "
          f"out={u.get('output_tokens', 0):,}")
    tail = (r.get("verify_tail") or "").replace("\n", " ")
    print(f"  verify: ...{tail[-150:]}")
    cj = d / "calls.jsonl"
    if cj.exists():
        lines = [json.loads(x) for x in cj.read_text(encoding="utf-8").splitlines() if x.strip()]
        print(f"  呼び出し {len(lines)} 件:")
        for c in lines:
            print(f"    {c.get('task_id'):<10} resumed={str(c.get('resumed')):<5} "
                  f"rc={c.get('returncode')} cr={c.get('cache_read_tokens') or 0:>9,} "
                  f"cost=${c.get('cost_usd') or 0:.4f} err={str(c.get('error'))[:60]}")
    else:
        print("  calls.jsonl なし")
    print()


if __name__ == "__main__":
    label = sys.argv[1]
    spec = sys.argv[2]
    for arm in ("B", "C"):
        for rep in (1, 2, 3):
            show(label, spec, arm, rep)
