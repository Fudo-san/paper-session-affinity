"""副次の感度分析（exclusion_rules §5 が副次に限って許可）。

主要判定には使わない。§8 に併記するための参考値。
  (a) 対内間隔が長い11対（rep1-2・アーム主体層）を除いた場合
  (b) ct_library を除いた場合
"""
import json
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/fudo1/project/paper-session-affinity")
sys.path.insert(0, str(ROOT / "analysis"))
from stats import bca_ci, paired_permutation_p  # noqa: E402

d = json.loads((ROOT / "analysis" / "e1_dataset_main.json").read_text(encoding="utf-8"))
pairs = d["pairs"]
RUNS = ROOT / "runs" / "main"


def gap_min(p):
    t = {}
    for arm in ("B", "C"):
        rj = RUNS / p["spec"] / arm / f"rep{p['rep']}" / "run.json"
        x = json.loads(rj.read_text(encoding="utf-8"))
        end = datetime.fromisoformat(x["iso"]).timestamp()
        t[arm] = (end - (x.get("wall_s") or 0), end)
    a, b = sorted(t.values(), key=lambda v: v[0])
    return (b[0] - a[1]) / 60


def report(name, sub):
    rel = [(p["cost_C"] - p["cost_B"]) / p["cost_B"] for p in sub]
    absd = [p["cost_C"] - p["cost_B"] for p in sub]
    p_val = paired_permutation_p(absd)
    lo, hi = bca_ci(absd, conf=0.95)
    print(f"{name}")
    print(f"  n={len(sub)}  相対差 中央値 {st.median(rel):+.1%}  平均 {st.mean(rel):+.1%}")
    print(f"  p={p_val:.4f}  BCa95%CI(絶対差USD)=[{lo:+.4f}, {hi:+.4f}]  "
          f"0を跨ぐ={'はい' if lo < 0 < hi else 'いいえ'}")
    print(f"  C が安い対: {sum(1 for r in rel if r < 0)}/{len(rel)}")
    print()


report("【主要判定】全98対", pairs)

far = [p for p in pairs if gap_min(p) >= 10]
near = [p for p in pairs if gap_min(p) < 10]
report(f"(a) 離隔層{len(far)}対を除外（仕様主体の隣接層のみ）", near)

no_ct = [p for p in pairs if p["spec"] != "ct_library"]
report("(b) ct_library を除外", no_ct)

both = [p for p in near if p["spec"] != "ct_library"]
report("(a)+(b) 両方を除外", both)
