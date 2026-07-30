import io
import json
import statistics as st
from pathlib import Path

rs = [json.loads(l) for l in io.open(
    Path(__file__).parent / "resume_probe_results.jsonl", encoding="utf-8")]

v = [r for r in rs if str(r.get("label", "")).endswith("_verdict")
     and r.get("mode") == "warm" and r.get("nonce")]

print("=== M1 (nonce付き = 有効測定) ===")
print(f"{'rep':<5}{'verdict':<10}{'H':>9}{'cache_r':>10}{'read/H':>9}{'ratio':>9}{'1/x':>8}")
ratios = []
for r in v:
    rr = r["cost_ratio_resume_over_init"]
    ratios.append(rr)
    print(f"{r['rep']:<5}{r['verdict']:<10}{r['H']:>9,}{r['cache_r_resume']:>10,}"
          f"{r['cache_r_resume']/r['H']:>9.4f}{rr:>9.4f}{1/rr:>8.1f}")

warm_n = sum(1 for r in v if r["verdict"] == "warm")
print(f"\nwarm: {warm_n}/{len(v)}")
print(f"cost_ratio 中央値 {st.median(ratios):.4f} = 1/{1/st.median(ratios):.1f}"
      f"   範囲 1/{1/max(ratios):.1f} 〜 1/{1/min(ratios):.1f}")
print(f"read/H 最小 {min(r['cache_r_resume']/r['H'] for r in v):.4f}  (H4(a)基準 >= 0.90)")

print("\n=== 内訳（分散の出どころ） ===")
for kind in ("init", "resume"):
    for r in [x for x in rs if str(x.get("label", "")).endswith(f"_{kind}")
              and x.get("nonce") and x.get("rc") == 0]:
        print(f"  {kind:<7}rep{r['rep']}: cache_w={r['cache_w']:>7,} "
              f"cache_r={r['cache_r']:>7,} cost=${r['cost_usd']:.5f}")
