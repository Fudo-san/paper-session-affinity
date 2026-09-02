#!/usr/bin/env python3
"""E2: H1〜H4 の判定とゲート構造（`protocol/rqs_hypotheses.md` §3-§4 の実装）.

本実験のデータが存在しない時点で書く（`pre_pilot_decisions.md` 決定4）。

## 判定規則（事前登録済み。ここでは実装するだけで、解釈を足さない）

- **H1（RQ1・費用）**: 対応付き置換検定（10,000再標本・両側 α=0.05）で有意、かつ
  BCa 95%CI が 0 を跨がない。「実質的削減」は**中央値ベースで ≥20% 削減**。
- **H2（RQ2・時間の非劣性）**: median(T_C) ≤ median(T_B) × (1 + 0.15)。
  bootstrap BCa 片側CI で判定。
- **H3（RQ3・品質の非劣性）**: 通過率差（C−B）の片側90%CI 下限 > −10pp。
- **H4(b)（モデル検証）**: 仕様ごとの費用比 r = Cost_C/Cost_B の実測が、
  `model_predictions.json` の r̂ に対し**相対誤差 ±25% 以内**が**過半数**の仕様で成立し、
  かつ**優劣の符号の予測が全仕様で一致**する。

## 中心主張の決定規則（§4）

  RQ1有意 ∧ ≥20%削減 ∧ RQ2成立 ∧ RQ3成立  のときだけ中心主張を掲げられる。
  **部分成立はそのまま部分成立として報告する。スピンしない。**

出力: `analysis/e2_results_<label>.json` と標準出力の要約。
"""
from __future__ import annotations

import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))

from stats import (  # noqa: E402
    bca_ci,
    bca_one_sided,
    median_ratio_ci,
    paired_permutation_p,
)

ALPHA = 0.05
SUBSTANTIAL_REDUCTION = 0.20   # §3 H1「実質的削減」
DELTA_TIME = 0.15              # non_inferiority.md §2
DELTA_Q_PP = 10.0              # non_inferiority.md §1（pp）
H4B_TOLERANCE = 0.25           # §3 H4(b) 相対誤差


def h1_cost(pairs: list[dict]) -> dict:
    """費用の対応付き比較。差は C − B（負なら C が安い）。"""
    diffs = [p["cost_C"] - p["cost_B"] for p in pairs]
    rel = [(p["cost_C"] - p["cost_B"]) / p["cost_B"] for p in pairs if p["cost_B"]]
    p_value = paired_permutation_p(diffs)
    lo, hi = bca_ci(diffs, conf=1.0 - ALPHA)
    med_rel = st.median(rel) if rel else 0.0
    significant = (p_value < ALPHA) and not (lo <= 0.0 <= hi)
    return {
        "n": len(pairs),
        "median_relative_diff": round(med_rel, 4),
        "mean_abs_diff_usd": round(st.mean(diffs), 4) if diffs else 0.0,
        "p_value": round(p_value, 5),
        "ci95_abs_diff_usd": [round(lo, 4), round(hi, 4)],
        "significant": significant,
        # 「削減」は負の相対差。中央値で -20% 以下なら実質的削減
        "substantial_reduction": med_rel <= -SUBSTANTIAL_REDUCTION,
        "direction": ("C_cheaper" if med_rel < 0 else
                      "C_more_expensive" if med_rel > 0 else "equal"),
    }


def h2_time(pairs: list[dict]) -> dict:
    """時間の非劣性。比 median(T_C)/median(T_B) の片側CI上限 < 1.15。"""
    tb = [p["wall_B"] for p in pairs]
    tc = [p["wall_C"] for p in pairs]
    # stats.median_ratio_ci(b_values, c_values) は median(C)/median(B) を返す
    point, upper = median_ratio_ci(tb, tc, conf=0.90)
    return {
        "median_T_B": round(st.median(tb), 2) if tb else 0.0,
        "median_T_C": round(st.median(tc), 2) if tc else 0.0,
        "ratio_point": round(point, 4),
        "ratio_ci_upper": round(upper, 4),
        "delta_time": DELTA_TIME,
        "non_inferior": upper < (1.0 + DELTA_TIME),
    }


def h3_quality(pairs: list[dict]) -> dict:
    """品質の非劣性。通過率差（C−B）の片側90%CI 下限 > −10pp。"""
    diffs_pp = [(p["accepted_C"] - p["accepted_B"]) * 100.0 for p in pairs]
    rate_b = st.mean([p["accepted_B"] for p in pairs]) * 100 if pairs else 0.0
    rate_c = st.mean([p["accepted_C"] for p in pairs]) * 100 if pairs else 0.0
    lower = bca_one_sided(diffs_pp, conf=0.90, side="lower")
    return {
        "pass_rate_B_pct": round(rate_b, 1),
        "pass_rate_C_pct": round(rate_c, 1),
        "diff_pp": round(rate_c - rate_b, 1),
        "ci90_lower_pp": round(lower, 2),
        "delta_q_pp": DELTA_Q_PP,
        "non_inferior": lower > -DELTA_Q_PP,
    }


def h4b_model(pairs: list[dict], preds: dict) -> dict:
    """モデルの端到端検証。仕様ごとの r を r̂ と突き合わせる。"""
    by_spec: dict[str, list[dict]] = defaultdict(list)
    for p in pairs:
        by_spec[p["spec"]].append(p)

    rows, within, sign_ok = [], 0, True
    for spec, ps in sorted(by_spec.items()):
        cb, cc = sum(p["cost_B"] for p in ps), sum(p["cost_C"] for p in ps)
        r = (cc / cb) if cb else None
        pred = (preds.get("specs", {}).get(spec, {})
                     .get("prediction", {}).get("r_hat"))
        rel_err = ((r - pred) / pred) if (r is not None and pred) else None
        ok = rel_err is not None and abs(rel_err) <= H4B_TOLERANCE
        within += 1 if ok else 0
        # 符号: どちらも「C が高い/安い」の向きが一致するか（1.0 を境に）
        if r is not None and pred:
            if (r > 1.0) != (pred > 1.0):
                sign_ok = False
        rows.append({"spec": spec, "n_pairs": len(ps),
                     "r_observed": round(r, 4) if r else None,
                     "r_hat": pred,
                     "rel_error": round(rel_err, 4) if rel_err is not None else None,
                     "within_tolerance": ok})
    n = len(rows)
    return {
        "tolerance": H4B_TOLERANCE,
        "specs": rows,
        "within_tolerance_count": within,
        "n_specs": n,
        "majority_within": (within * 2 > n) if n else False,
        "sign_agreement": sign_ok,
        "verdict": bool(n and (within * 2 > n) and sign_ok),
    }


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "main"
    ds_path = ROOT / "analysis" / f"e1_dataset_{label}.json"
    if not ds_path.exists():
        print(f"[ERROR] E1 の出力が無い: {ds_path}\n"
              f"  先に `python3 analysis/e1_aggregate.py {label}` を実行すること",
              file=sys.stderr)
        return 1
    ds = json.loads(ds_path.read_text(encoding="utf-8"))

    # 停止条件は既定で判定を止める。`exclusion_rules.md` §3 は
    # 「停止し、原因を調査してから再開する。**再開時は Amendment Log に記録する**」
    # と定めており、記録済みの再開判断がある場合にだけ通す口を用意する。
    # 閾値そのものは書き換えない（データを見た後にコードを緩める形を避けるため）。
    # 通した場合は Amendment ID を判定結果に必ず刻む。
    ack = None
    for i, a in enumerate(sys.argv):
        if a == "--acknowledge-stop" and i + 1 < len(sys.argv):
            ack = sys.argv[i + 1]
    if ds.get("stop_conditions"):
        if not ack:
            print("*** E1 が停止条件を検出している。判定を出さない。 ***")
            for s in ds["stop_conditions"]:
                print(f"  - {s}")
            print("\n  再開するには exclusion_rules §3 に従って原因を調査し、"
                  "Amendment Log へ記録したうえで")
            print("  `--acknowledge-stop <Amendment ID>` を付けて実行すること。")
            return 2
        print("*** 停止条件あり。記録済みの再開判断により続行する。 ***")
        for s in ds["stop_conditions"]:
            print(f"  - {s}")
        print(f"  → 根拠: protocol/rqs_hypotheses.md §7 {ack}")
        print()

    pairs = ds["pairs"]
    if len(pairs) < 2:
        print(f"[ERROR] 有効ペアが {len(pairs)} 件しかない。判定不能。", file=sys.stderr)
        return 1

    pred_path = ROOT / "analysis" / "model_predictions.json"
    if pred_path.exists():
        preds = json.loads(pred_path.read_text(encoding="utf-8"))
        h4 = h4b_model(pairs, preds)
    else:
        # R1 の要件: 予測ファイルが無ければ「判定不能」と明示し、黙って飛ばさない
        h4 = {"verdict": None,
              "note": "model_predictions.json が無いため H4(b) は判定不能。"
                      "実測を見てから予測を作ることは禁止（§3.8.4）。"}

    h1, h2, h3 = h1_cost(pairs), h2_time(pairs), h3_quality(pairs)
    central = bool(h1["significant"] and h1["substantial_reduction"]
                   and h2["non_inferior"] and h3["non_inferior"])

    out = {"label": label, "generated_by": "analysis/e2_tests.py",
           "n_pairs": len(pairs), "alpha": ALPHA,
           "H1_cost": h1, "H2_time": h2, "H3_quality": h3, "H4b_model": h4,
           "central_claim_supported": central,
           "decision_rule": "RQ1有意 ∧ 中央値-20%以下 ∧ RQ2非劣性 ∧ RQ3非劣性 の全成立時のみ",
           "note": "部分成立は部分成立のまま報告する（§4）。スピンしない。"}
    dest = ROOT / "analysis" / f"e2_results_{label}.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    def mark(b) -> str:
        return "成立" if b else ("判定不能" if b is None else "不成立")

    print(f"=== E2 ({label})  n={len(pairs)} ペア ===")
    print(f"H1 費用   : 中央値 {h1['median_relative_diff']:+.1%}  p={h1['p_value']}  "
          f"CI95={h1['ci95_abs_diff_usd']}  有意={mark(h1['significant'])}  "
          f"≥20%削減={mark(h1['substantial_reduction'])}")
    print(f"H2 時間   : 比 {h2['ratio_point']:.3f} (CI上限 {h2['ratio_ci_upper']:.3f} "
          f"< {1 + DELTA_TIME})  非劣性={mark(h2['non_inferior'])}")
    print(f"H3 品質   : B {h3['pass_rate_B_pct']}% → C {h3['pass_rate_C_pct']}%  "
          f"差 {h3['diff_pp']:+.1f}pp  CI90下限 {h3['ci90_lower_pp']:+.2f}pp  "
          f"非劣性={mark(h3['non_inferior'])}")
    if h4.get("verdict") is None:
        print(f"H4b モデル: 判定不能 — {h4.get('note', '')}")
    else:
        print(f"H4b モデル: 許容内 {h4['within_tolerance_count']}/{h4['n_specs']} "
              f"(過半数={mark(h4['majority_within'])})  "
              f"符号一致={mark(h4['sign_agreement'])}  総合={mark(h4['verdict'])}")
        for r in h4["specs"]:
            e = f"{r['rel_error']:+.1%}" if r["rel_error"] is not None else "n/a"
            print(f"    {r['spec']:<18} r={r['r_observed']}  r̂={r['r_hat']}  誤差 {e}")

    print(f"\n中心主張: {'掲げられる' if central else '掲げられない（部分成立はそのまま報告）'}")
    print(f"→ {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
