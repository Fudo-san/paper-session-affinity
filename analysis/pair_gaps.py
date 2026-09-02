"""対内の B/C 実行間隔を実測する（A-5 による層の非均質性の定量化）。

アーム主体では B と C の間に他仕様6本が挟まる。仕様主体では隣接する。
実際にどれだけ離れていたかを run.json の時刻から測る。
"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs" / "main"
specs = [s["spec_id"] for s in json.loads(
    (ROOT / "benchmarks" / "specs.json").read_text(encoding="utf-8"))["specs"]]

gaps = []
for rep in range(1, 15):
    for spec in specs:
        t = {}
        for arm in ("B", "C"):
            rj = RUNS / spec / arm / f"rep{rep}" / "run.json"
            if not rj.exists():
                continue
            d = json.loads(rj.read_text(encoding="utf-8"))
            # iso は完了時刻。wall_s を引いて開始時刻を出す
            end = datetime.fromisoformat(d["iso"])
            t[arm] = (end.timestamp() - (d.get("wall_s") or 0), end.timestamp())
        if len(t) == 2:
            # 先に終わった方の終了 → 後に始まった方の開始 までの間隔
            first, second = sorted(t.values(), key=lambda x: x[0])
            gap_min = (second[0] - first[1]) / 60
            gaps.append((rep, spec, gap_min))

gaps.sort(key=lambda x: x[2])
short = [g for g in gaps if g[2] < 10]
long_ = [g for g in gaps if g[2] >= 10]

print(f"対の総数: {len(gaps)}")
print(f"  間隔 10分未満（隣接＝仕様主体）: {len(short)} 対")
print(f"  間隔 10分以上（離隔＝アーム主体または中断跨ぎ）: {len(long_)} 対")
print()
vals = [g[2] for g in gaps]
vals.sort()
n = len(vals)
print(f"間隔の分布（分）: 最小 {vals[0]:.1f} / 中央 {vals[n//2]:.1f} / 最大 {vals[-1]:.1f}")
print()
print("=== 間隔が長かった対 上位12 ===")
for rep, spec, g in sorted(gaps, key=lambda x: -x[2])[:12]:
    print(f"  rep{rep:<3}{spec:<18}{g:>9.1f} 分")
print()
print("=== 反復ごとの中央間隔 ===")
for rep in range(1, 15):
    v = sorted(g[2] for g in gaps if g[0] == rep)
    if v:
        print(f"  rep{rep:<3}n={len(v):<3}中央 {v[len(v)//2]:>7.1f} 分   最大 {v[-1]:>7.1f} 分")
