#!/usr/bin/env python3
"""論文の図を生成する。

  ./.venv-figs/bin/python analysis/make_figures.py

同梱データ（e1_dataset_main.json）だけから作る。追加の測定はしない。
出力は paper/figures/ に PDF と PNG で置く（arXiv は PDF、README は PNG）。

図は主張に直結するものだけを作る。装飾のための図は作らない。
  fig1: 対ごとの相対差の分布 — 効果がほぼ拮抗していること
  fig2: 仕様別の相対差 — 単一仕様が符号を決めていること
  fig3: 予測 r̂ と実測 r — モデルが系統的に過大評価すること
  fig4: 履歴 H の軌跡（CT） — 代償の機構
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "figure.dpi": 150, "savefig.bbox": "tight", "axes.grid": True,
    "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False,
})

ds = json.loads((ROOT / "analysis" / "e1_dataset_main.json").read_text(encoding="utf-8"))
res = json.loads((ROOT / "analysis" / "e2_results_main.json").read_text(encoding="utf-8"))
pairs = ds["pairs"]


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}")
    plt.close(fig)
    print(f"  {name}.pdf / .png")


# --- fig1: 相対差の分布 -----------------------------------------------------
rel = [(p["cost_C"] - p["cost_B"]) / p["cost_B"] * 100 for p in pairs]
med = st.median(rel)
fig, ax = plt.subplots(figsize=(5.2, 2.9))
ax.hist(rel, bins=28, color="#4C72B0", edgecolor="white", linewidth=0.5)
ax.axvline(0, color="#444", lw=1.0, ls="-", label="no difference")
ax.axvline(med, color="#C44E52", lw=1.4, ls="--",
           label=f"median {med:+.1f}%")
ax.axvline(-20, color="#55A868", lw=1.2, ls=":",
           label="preregistered −20% threshold")
ax.set_xlabel("relative cost difference  (C − B) / B  [%]")
ax.set_ylabel("pairs")
ax.set_title(f"Paired cost difference (n = {len(rel)})")
ax.legend(fontsize=7, frameon=False)
save(fig, "fig1_paired_difference")

# --- fig2: 仕様別 -----------------------------------------------------------
by: dict[str, list[float]] = {}
for p in pairs:
    by.setdefault(p["spec"], []).append((p["cost_C"] - p["cost_B"]) / p["cost_B"] * 100)
order = sorted(by, key=lambda k: st.median(by[k]))
fig, ax = plt.subplots(figsize=(5.6, 3.2))
bp = ax.boxplot([by[k] for k in order], orientation="horizontal", tick_labels=order,
                widths=0.6, patch_artist=True, medianprops=dict(color="#C44E52", lw=1.4))
for patch, k in zip(bp["boxes"], order):
    patch.set_facecolor("#DD8452" if k == "ct_library" else "#4C72B0")
    patch.set_alpha(0.75)
ax.axvline(0, color="#444", lw=1.0)
ax.set_xlabel("relative cost difference  (C − B) / B  [%]")
ax.set_title("Per-specification distribution (14 pairs each)")
ax.tick_params(axis="y", labelsize=8)
save(fig, "fig2_per_spec")

# --- fig3: 予測 vs 実測 -----------------------------------------------------
specs = res["H4b_model"]["specs"]
fig, ax = plt.subplots(figsize=(4.2, 4.0))
lo, hi = 0.85, 1.65
ax.plot([lo, hi], [lo, hi], color="#888", lw=1.0, ls="--", label="perfect prediction")
for s in specs:
    ax.scatter(s["r_hat"], s["r_observed"], s=42,
               color="#DD8452" if s["spec"] == "ct_library" else "#4C72B0", zorder=3)
    ax.annotate(s["spec"], (s["r_hat"], s["r_observed"]), fontsize=6.5,
                xytext=(4, -8), textcoords="offset points")
ax.axhline(1.0, color="#C44E52", lw=0.9, ls=":", label="C = B")
ax.axvline(1.0, color="#C44E52", lw=0.9, ls=":")
ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
ax.set_xlabel(r"predicted cost ratio  $\hat{r}$")
ax.set_ylabel("observed cost ratio  r")
ax.set_title("Model predictions vs. observations")
ax.legend(fontsize=7, frameon=False, loc="upper left")
save(fig, "fig3_model_vs_observed")

# --- fig4: CT の履歴軌跡 ----------------------------------------------------
# CT パイロットの実測（runs/CT_PILOT_2026-08-24.md に記録済み）
h = [42534, 54212, 61046]
labels = ["CT-A\n(fresh)", "CT-B\n(resume)", "CT-C\n(resume)"]
delta = [None, 36.9, 35.5]
fig, ax = plt.subplots(figsize=(4.4, 2.9))
ax.plot(range(3), [x / 1000 for x in h], marker="o", color="#4C72B0", lw=1.6)
for i, (v, d) in enumerate(zip(h, delta)):
    txt = f"{v/1000:.1f}k" + (f"\n{d:+.1f}%" if d else "")
    ax.annotate(txt, (i, v / 1000), fontsize=7.5,
                xytext=(0, 10), textcoords="offset points", ha="center")
ax.set_xticks(range(3)); ax.set_xticklabels(labels, fontsize=8)
ax.set_ylabel("carried history H  [k tokens]")
ax.set_ylim(35, 70)
ax.set_title("History growth within a contended lane")
save(fig, "fig4_history_growth")

print(f"\n出力先: {OUT}")
