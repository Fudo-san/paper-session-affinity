"""統計プリミティブ。

`protocol/rqs_hypotheses.md`（FROZEN）が要求する2つの手法だけを実装する。

- 対応付き置換検定（符号反転・両側・10,000再標本）
- BCa ブートストラップ信頼区間（両側・片側）

標準ライブラリのみで書く。再現パッケージを配るときに依存で詰まらせないため、
また `statistics.NormalDist` が BCa に必要な正規分布の CDF / 逆CDF を
持っているため、外部パッケージを入れる理由がない。

このモジュールは**合成データで検証する**（tests/test_stats.py）。
実験データで挙動を確かめると、分析手法を結果に合わせて調整できてしまう。
"""
from __future__ import annotations

import random
from statistics import NormalDist, mean, median
from typing import Callable, Sequence

SEED = 20260802          # PRE_ANALYSIS_DECISIONS.md 決定D
N_RESAMPLES = 10_000     # rqs_hypotheses.md §3 H1
_ND = NormalDist()

Statistic = Callable[[Sequence[float]], float]


def paired_permutation_p(
    diffs: Sequence[float],
    statistic: Statistic = mean,
    n_resamples: int = N_RESAMPLES,
    seed: int = SEED,
) -> float:
    """対応付き置換検定の両側 p 値。

    帰無仮説は「各対の差の符号が交換可能」（PRE_ANALYSIS_DECISIONS 決定C）。
    差の符号をランダムに反転して帰無分布を作る。

    既定の統計量は**平均**（決定B）。中央値は差の大きさを無視するため、
    符号反転検定の統計量としては検出力が著しく低い。極端な例として、
    差が全て同じ大きさなら中央値は 82% の確率で観測値と同じ大きさになり、
    検定がまったく効かない。実質性（≥20%）の判定には凍結文書どおり
    中央値を使うが、それは別の役割である。

    p = (|統計量| が観測値以上になった回数 + 1) / (再標本数 + 1)
    Phipson & Smyth の補正。p が 0 になると「p < 0.0001」を「p = 0」と
    書いてしまうため、最小値を 1/(n+1) で止める。
    """
    if len(diffs) < 2:
        raise ValueError("対が2つ未満では検定できない")
    obs = abs(statistic(diffs))
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_resamples):
        flipped = [d if rng.random() < 0.5 else -d for d in diffs]
        # 浮動小数の等値ぶれで「ちょうど同じ」を取りこぼさないための微小許容
        if abs(statistic(flipped)) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (n_resamples + 1)


def _bootstrap_distribution(
    data: Sequence[float],
    statistic: Statistic,
    n_boot: int,
    seed: int,
) -> list[float]:
    rng = random.Random(seed)
    n = len(data)
    out = []
    for _ in range(n_boot):
        sample = [data[rng.randrange(n)] for _ in range(n)]
        out.append(statistic(sample))
    out.sort()
    return out


def _bca_params(
    data: Sequence[float],
    statistic: Statistic,
    boots: Sequence[float],
) -> tuple[float, float]:
    """バイアス補正 z0 と加速度 a を返す。

    z0: ブートストラップ分布のうち観測値を下回る割合を正規変換したもの。
    a : ジャックナイフ（1個ずつ抜く）による歪みの尺度。
    """
    obs = statistic(data)
    n_boot = len(boots)
    prop = sum(1 for b in boots if b < obs) / n_boot
    # 0 と 1 は inv_cdf が発散する。両端を 1/(2*n_boot) で内側に寄せる。
    lo = 1.0 / (2 * n_boot)
    prop = min(max(prop, lo), 1.0 - lo)
    z0 = _ND.inv_cdf(prop)

    n = len(data)
    jack = [statistic(list(data[:i]) + list(data[i + 1:])) for i in range(n)]
    jbar = mean(jack)
    num = sum((jbar - x) ** 3 for x in jack)
    den = 6.0 * (sum((jbar - x) ** 2 for x in jack) ** 1.5)
    a = num / den if den else 0.0
    return z0, a


def bca_quantile(
    data: Sequence[float],
    statistic: Statistic = median,
    p: float = 0.025,
    n_boot: int = N_RESAMPLES,
    seed: int = SEED,
) -> float:
    """BCa 補正した p 分位点。CI はこれを組み合わせて作る。"""
    if len(data) < 3:
        raise ValueError("ジャックナイフに3点以上必要")
    boots = _bootstrap_distribution(data, statistic, n_boot, seed)
    z0, a = _bca_params(data, statistic, boots)
    z = _ND.inv_cdf(p)
    denom = 1.0 - a * (z0 + z)
    if denom == 0:
        adj = p
    else:
        adj = _ND.cdf(z0 + (z0 + z) / denom)
    idx = int(round(adj * (n_boot - 1)))
    return boots[min(max(idx, 0), n_boot - 1)]


def bca_ci(
    data: Sequence[float],
    statistic: Statistic = median,
    conf: float = 0.95,
    n_boot: int = N_RESAMPLES,
    seed: int = SEED,
) -> tuple[float, float]:
    """両側 BCa 信頼区間。"""
    alpha = 1.0 - conf
    lo = bca_quantile(data, statistic, alpha / 2, n_boot, seed)
    hi = bca_quantile(data, statistic, 1.0 - alpha / 2, n_boot, seed)
    return lo, hi


def bca_one_sided(
    data: Sequence[float],
    statistic: Statistic = median,
    conf: float = 0.90,
    side: str = "lower",
    n_boot: int = N_RESAMPLES,
    seed: int = SEED,
) -> float:
    """片側 BCa 限界。

    side="lower": 下限（H3 の「差の片側90%CI 下限 > −δ_q」用）
    side="upper": 上限（H2 の「比の片側CI 上限 < 1+δ_time」用）
    """
    if side == "lower":
        return bca_quantile(data, statistic, 1.0 - conf, n_boot, seed)
    if side == "upper":
        return bca_quantile(data, statistic, conf, n_boot, seed)
    raise ValueError(f"side は lower か upper: {side}")


def median_ratio_ci(
    b_values: Sequence[float],
    c_values: Sequence[float],
    conf: float = 0.90,
    n_boot: int = N_RESAMPLES,
    seed: int = SEED,
) -> tuple[float, float]:
    """median(C)/median(B) の点推定と片側上限。

    H2（時間の非劣性）は中央値の**比**に対する判定なので、対ごとの差ではなく
    2群それぞれの中央値から比を作る。対応を保つため、ブートストラップは
    **対単位**で再標本する（同じ添字の B と C を一緒に取る）。
    """
    if len(b_values) != len(c_values):
        raise ValueError("B と C の件数が違う")
    n = len(b_values)
    point = median(c_values) / median(b_values)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        mb = median([b_values[i] for i in idx])
        mc = median([c_values[i] for i in idx])
        if mb:
            boots.append(mc / mb)
    boots.sort()
    # 比は歪むのでジャックナイフ加速も入れる
    pairs = list(zip(b_values, c_values))

    def ratio_stat(sample: Sequence[tuple[float, float]]) -> float:
        return median([c for _, c in sample]) / median([b for b, _ in sample])

    n_boot_eff = len(boots)
    prop = sum(1 for x in boots if x < point) / n_boot_eff
    lo = 1.0 / (2 * n_boot_eff)
    prop = min(max(prop, lo), 1.0 - lo)
    z0 = _ND.inv_cdf(prop)
    jack = [ratio_stat(pairs[:i] + pairs[i + 1:]) for i in range(n)]
    jbar = mean(jack)
    num = sum((jbar - x) ** 3 for x in jack)
    den = 6.0 * (sum((jbar - x) ** 2 for x in jack) ** 1.5)
    a = num / den if den else 0.0
    z = _ND.inv_cdf(conf)
    denom = 1.0 - a * (z0 + z)
    adj = _ND.cdf(z0 + (z0 + z) / denom) if denom else conf
    idx = int(round(adj * (n_boot_eff - 1)))
    return point, boots[min(max(idx, 0), n_boot_eff - 1)]
