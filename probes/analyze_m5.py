import io
import json
from pathlib import Path

rs = [json.loads(l) for l in io.open(
    Path(__file__).parent / "m5_results.jsonl", encoding="utf-8")]

print("=== 呼び出しごと（再探索コスト E の可視化） ===")
print(f"{'arm/task':<12}{'turns':>6}{'cache_w':>9}{'cache_r':>10}{'cost':>10}{'wall':>8}")
for r in rs:
    if r.get("label") in ("task1", "task2"):
        print(f"{r['arm']}/{r['label']:<9}{r['num_turns']:>6}{r['cache_w']:>9,}"
              f"{r['cache_r']:>10,}{r['cost_usd']:>10.4f}{r['wall_s']:>8.1f}")

s = [r for r in rs if r.get("label") == "m5_summary"]
if s:
    s = s[-1]
    print("\n=== アーム合計 ===")
    print(f"  B (fresh) : ${s['B_cost']:.4f}  wall={s['B_wall']}s  cache_r={s['B_cache_r']:,}")
    print(f"  C (resume): ${s['C_cost']:.4f}  wall={s['C_wall']}s  cache_r={s['C_cache_r']:,}")
    print(f"  C/B = {s['cost_ratio_C_over_B']}   費用削減 {s['saving_pct']}%")
    print(f"  時間比 = {s['C_wall']/s['B_wall']:.3f}（C の方が短い場合 <1）")
