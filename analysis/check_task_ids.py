#!/usr/bin/env python3
"""calls.jsonl の task_id が全件埋まっているかを確認する.

背景: task_id は共有フィールド経由で渡されており、並列 developer 実行で
取り違え・欠落が起きていた（fail-20260825-01）。較正 (R1) はレーンとの
突き合わせに task_id を使うため、欠落があると予測値が壊れる。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/calib")
empty_total = 0
dup_total = 0
for p in sorted(root.rglob("calls.jsonl")):
    rows = [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]
    if not rows:
        continue
    ids = [r.get("task_id") for r in rows]
    turns = [r.get("num_turns") for r in rows]
    empty = sum(1 for i in ids if not i)
    dup = len(ids) - len(set(ids))
    empty_total += empty
    dup_total += dup
    flag = "" if (empty == 0 and dup == 0) else "  <-- 問題"
    print(f"{rows[0].get('spec'):<18} task_ids={ids} turns={turns}{flag}")

print(f"\n空の task_id: {empty_total} 件 / 重複: {dup_total} 件")
if empty_total == 0 and dup_total == 0:
    print("OK: 全件が一意に埋まっている（修正が効いている）")
    sys.exit(0)
print("NG: 較正に使えない。原因を解消してから再取得すること")
sys.exit(1)
