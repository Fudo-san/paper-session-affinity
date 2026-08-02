"""stats.py の検証。

**合成データだけを使う。** 実験データ（runs/）は読まない。
実データで挙動を確かめると、分析手法を結果に合わせて調整でき、
本実験の結果を先に覗くことにもなる。

各テストは「答えが分かっている入力」に対して期待どおりかを見る。
"""
from __future__ import annotations

import random
import sys
from pathlib import Path
from statistics import mean, median

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stats import (  # noqa: E402
    bca_ci,
    bca_one_sided,
    median_ratio_ci,
    paired_permutation_p,
)

# ---------------------------------------------------------------------------
# 対応付き置換検定
# ---------------------------------------------------------------------------


def test_all_same_sign_gives_minimum_p():
    """全対が同符号で大きい差なら、符号反転でこれを超えるのはほぼ不可能。

    既定の統計量は平均。n=20 で全て +1 なら平均は 1.0。符号反転して |平均| が
    1.0 以上になるのは全て同符号を引いたときだけで、確率 2/2^20 ≈ 2e-6。
    10,000 再標本ではまず出ないので、p は下限 1/10001 に張り付く。
    """
    diffs = [1.0] * 20
    p = paired_permutation_p(diffs)
    assert p == pytest.approx(1 / 10001, abs=1e-6)


def test_median_is_a_poor_permutation_statistic():
    """中央値を符号反転検定の統計量にしてはならない理由（決定Bの根拠）。

    差が全て同じ大きさ 1.0 の20対では、符号反転後の中央値は
    正が11個以上なら +1、9個以下なら −1 になる。ちょうど10個のときだけ 0。
    つまり 82% ほどの確率で |中央値| が観測値と並び、p 値が跳ね上がる。

    中央値は差の**大きさ**を捨てるため、大きさの情報しかない入力では
    まったく検出できない。実データではここまで極端にならないが、
    検出力が落ちる性質は同じである。
    """
    diffs = [1.0] * 20
    p_median = paired_permutation_p(diffs, statistic=median)
    p_mean = paired_permutation_p(diffs, statistic=mean)
    assert p_median > 0.5, "中央値では検出できない（これが使わない理由）"
    assert p_mean < 0.001, "平均なら正しく検出する"


def test_symmetric_data_is_not_significant():
    """符号が釣り合ったデータは有意にならない。"""
    diffs = [1.0, -1.0] * 10
    p = paired_permutation_p(diffs)
    assert p > 0.5


def test_p_is_never_zero():
    """Phipson & Smyth 補正により p=0 は出ない。"""
    diffs = [100.0] * 30
    assert paired_permutation_p(diffs) > 0


def test_p_is_deterministic_with_fixed_seed():
    """種を固定すれば同じ p が出る（再現性・決定D）。"""
    rng = random.Random(1)
    diffs = [rng.gauss(0.3, 1.0) for _ in range(18)]
    assert paired_permutation_p(diffs) == paired_permutation_p(diffs)


def test_sign_flip_invariance():
    """全体の符号を反転しても両側 p は変わらない。"""
    rng = random.Random(2)
    diffs = [rng.gauss(0.4, 1.0) for _ in range(18)]
    flipped = [-d for d in diffs]
    assert paired_permutation_p(diffs) == pytest.approx(
        paired_permutation_p(flipped), abs=0.02)


def test_larger_effect_gives_smaller_p():
    """効果が大きいほど p は小さくなる。"""
    rng = random.Random(3)
    base = [rng.gauss(0.0, 1.0) for _ in range(24)]
    weak = [x + 0.3 for x in base]
    strong = [x + 2.0 for x in base]
    assert paired_permutation_p(strong) < paired_permutation_p(weak)


def test_rejects_too_few_pairs():
    with pytest.raises(ValueError):
        paired_permutation_p([1.0])


# ---------------------------------------------------------------------------
# BCa ブートストラップ
# ---------------------------------------------------------------------------


def test_bca_ci_contains_the_point_estimate():
    rng = random.Random(4)
    data = [rng.gauss(5.0, 1.0) for _ in range(40)]
    lo, hi = bca_ci(data, statistic=median, conf=0.95)
    assert lo <= median(data) <= hi


def test_bca_ci_is_ordered():
    rng = random.Random(5)
    data = [rng.gauss(0.0, 1.0) for _ in range(30)]
    lo, hi = bca_ci(data)
    assert lo < hi


def test_bca_ci_narrows_as_n_grows():
    """標本が増えれば区間は狭くなる。"""
    rng = random.Random(6)
    small = [rng.gauss(0.0, 1.0) for _ in range(10)]
    large = [rng.gauss(0.0, 1.0) for _ in range(200)]
    w_small = lambda d: (lambda t: t[1] - t[0])(bca_ci(d))  # noqa: E731
    assert w_small(large) < w_small(small)


def test_bca_mean_ci_approximates_normal_theory():
    """対称な正規データでは、平均の BCa 95%CI が平均±1.96SE に近づく。

    BCa は歪みが無ければ通常のパーセンタイル法に一致し、
    それは大標本で正規理論に一致する。
    """
    rng = random.Random(7)
    n = 400
    data = [rng.gauss(10.0, 2.0) for _ in range(n)]
    lo, hi = bca_ci(data, statistic=mean, conf=0.95)
    se = 2.0 / (n ** 0.5)
    assert lo == pytest.approx(mean(data) - 1.96 * se, abs=0.15)
    assert hi == pytest.approx(mean(data) + 1.96 * se, abs=0.15)


def test_bca_shifts_with_the_data():
    """データを定数だけずらせば区間も同じだけずれる。"""
    rng = random.Random(8)
    data = [rng.gauss(0.0, 1.0) for _ in range(50)]
    shifted = [x + 100.0 for x in data]
    lo1, hi1 = bca_ci(data, statistic=median)
    lo2, hi2 = bca_ci(shifted, statistic=median)
    assert lo2 - lo1 == pytest.approx(100.0, abs=0.3)
    assert hi2 - hi1 == pytest.approx(100.0, abs=0.3)


def test_one_sided_bounds_are_inside_two_sided():
    """片側90%の限界は、両側95%の対応する端より内側にある。"""
    rng = random.Random(9)
    data = [rng.gauss(1.0, 1.0) for _ in range(40)]
    lo95, hi95 = bca_ci(data, conf=0.95)
    lo90 = bca_one_sided(data, conf=0.90, side="lower")
    hi90 = bca_one_sided(data, conf=0.90, side="upper")
    assert lo90 >= lo95
    assert hi90 <= hi95


def test_bca_rejects_tiny_samples():
    with pytest.raises(ValueError):
        bca_ci([1.0, 2.0])


# ---------------------------------------------------------------------------
# 中央値の比（H2 用）
# ---------------------------------------------------------------------------


def test_identical_arms_give_ratio_one():
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    point, upper = median_ratio_ci(values, list(values), conf=0.90)
    assert point == pytest.approx(1.0)
    assert upper == pytest.approx(1.0, abs=1e-9)


def test_known_ratio_is_recovered():
    """C が B の一定倍なら、比の点推定はその倍率になる。"""
    b = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    c = [x * 1.20 for x in b]
    point, _ = median_ratio_ci(b, c)
    assert point == pytest.approx(1.20, abs=1e-9)


def test_ratio_upper_bound_is_above_point():
    rng = random.Random(10)
    b = [rng.gauss(100.0, 10.0) for _ in range(30)]
    c = [x * 1.05 + rng.gauss(0, 5) for x in b]
    point, upper = median_ratio_ci(b, c, conf=0.90)
    assert upper >= point


def test_ratio_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        median_ratio_ci([1.0, 2.0], [1.0])
