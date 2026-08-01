#!/usr/bin/env python3
"""未実行スプリントの棚卸し。

agent-framework は `<project>-spec/sprint_N/` を読んで実行し、実行側リポの
`sprints/<sprint_id>/sprint_done.json` に完了記録を残す。
「spec は書かれているが完了記録が無い」スプリントは、**native 形式のまま
使えるベンチマーク候補**である（plan.json への手作業変換が要らない）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path.home() / "project"


def impl_dir_for(spec_dir: Path) -> Path:
    return ROOT / spec_dir.name.replace("-spec", "")


def sprint_num(p: Path) -> int:
    m = re.search(r"sprint_(\d+)", p.name)
    return int(m.group(1)) if m else -1


rows = []
for spec_dir in sorted(ROOT.glob("*-spec")):
    impl = impl_dir_for(spec_dir)
    sprints = sorted([p for p in spec_dir.glob("sprint_*") if p.is_dir()],
                     key=sprint_num)
    for s in sprints:
        sid = s.name
        has_spec = (s / "project_spec.md").exists()
        has_cfg = (s / "sprint_config.json").exists()
        done = impl / "sprints" / sid / "sprint_done.json"
        plan = impl / "sprints" / sid / "plan.json"
        rows.append({
            "spec": spec_dir.name, "sprint": sid,
            "spec_md": has_spec, "cfg": has_cfg,
            "done": done.exists(), "plan": plan.exists(),
            "spec_lines": len((s / "project_spec.md").read_text(encoding="utf-8",
                                                                errors="replace").splitlines())
            if has_spec else 0,
        })

print(f"{'spec folder':<32}{'sprint':<12}{'spec.md':<9}{'cfg':<6}{'plan':<7}{'done':<7}{'lines':<6}")
for r in rows:
    print(f"{r['spec']:<32}{r['sprint']:<12}"
          f"{'✓' if r['spec_md'] else '—':<9}{'✓' if r['cfg'] else '—':<6}"
          f"{'✓' if r['plan'] else '—':<7}{'✓' if r['done'] else '—':<7}{r['spec_lines']:<6}")

print("\n=== 未実行候補（spec 有・done 無）===")
cand = [r for r in rows if r["spec_md"] and r["cfg"] and not r["done"]]
if not cand:
    print("  なし")
for r in cand:
    state = "plan途中" if r["plan"] else "未着手"
    print(f"  {r['spec']:<32}{r['sprint']:<12}{state:<10}spec {r['spec_lines']}行")
print(f"\n計 {len(cand)} 件")
