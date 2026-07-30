import io
import json
from pathlib import Path

rs = [json.loads(l) for l in io.open(
    Path(__file__).parent / "resume_probe_results.jsonl", encoding="utf-8")]


def pairs(mode: str, second_suffix: str):
    out = []
    for rep in sorted({r.get("rep") for r in rs if r.get("mode") == mode and r.get("rep")}):
        a = [r for r in rs if r.get("mode") == mode and r.get("rep") == rep
             and str(r.get("label", "")).endswith("_init") and r.get("rc") == 0]
        b = [r for r in rs if r.get("mode") == mode and r.get("rep") == rep
             and str(r.get("label", "")).endswith(second_suffix) and r.get("rc") == 0]
        if a and b:
            out.append((rep, a[-1], b[-1]))
    return out


print("=== M4 xsession: 同一プレフィックスで新規セッション2本 ===")
print(f"{'rep':<4}{'1本目 w':>10}{'1本目 r':>10}{'2本目 w':>10}{'2本目 r':>10}{'cost比':>9}  判定")
for rep, a, b in pairs("xsession", "_second"):
    ratio = b["cost_usd"] / a["cost_usd"]
    hit = "ヒットあり(γ≈α_r)" if b["cache_w"] < 0.5 * a["cache_w"] else "**ヒットなし(γ=1)**"
    print(f"{rep:<4}{a['cache_w']:>10,}{a['cache_r']:>10,}{b['cache_w']:>10,}"
          f"{b['cache_r']:>10,}{ratio:>9.3f}  {hit}")

print("\n=== M3 switch: モデル切替 resume ===")
print(f"{'rep':<4}{'H':>9}{'切替後 w':>10}{'切替後 r':>10}{'w+r':>9}{'(w+r)/H':>9}{'w/H':>7}{'cost比':>8}")
for rep, a, b in pairs("switch", "_resume"):
    h = a["cache_w"] + a["cache_r"]
    wr = b["cache_w"] + b["cache_r"]
    print(f"{rep:<4}{h:>9,}{b['cache_w']:>10,}{b['cache_r']:>10,}{wr:>9,}"
          f"{wr/h:>9.3f}{b['cache_w']/h:>7.3f}{b['cost_usd']/a['cost_usd']:>8.3f}")

print("\n=== 参照: M1 warm（同一モデル resume） ===")
print(f"{'rep':<4}{'H':>9}{'resume w':>10}{'resume r':>10}{'cost比':>8}")
for rep, a, b in pairs("warm", "_resume"):
    if not a.get("nonce"):
        continue
    h = a["cache_w"] + a["cache_r"]
    print(f"{rep:<4}{h:>9,}{b['cache_w']:>10,}{b['cache_r']:>10,}"
          f"{b['cost_usd']/a['cost_usd']:>8.3f}")
