"""Regression tests use synthetic inputs only; no tuning against research outcomes."""
import math
import statistics as st
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import revision_audit as audit

def test_quality_interval_targets_mean_not_median():
    pairs=[dict(accepted_B=1,accepted_C=0)]*2+[dict(accepted_B=1,accepted_C=1)]*18
    result=audit.corrected_quality(pairs)
    assert result['diff_pp']==-10
    assert result['ci90_lower_pp'] < -10
    assert not result['non_inferior']

def test_cost_analysis_is_invariant_to_pair_specific_currency_scales():
    ratios=[-.3,-.1,.02,.05,.08,.1,.15,.2]
    first=[dict(cost_B=1,cost_C=1+r) for r in ratios]
    second=[dict(cost_B=10**i,cost_C=10**i*(1+r)) for i,r in enumerate(ratios)]
    a,b=audit.corrected_cost(first),audit.corrected_cost(second)
    assert math.isclose(a['p_value'],b['p_value'])
    assert all(math.isclose(x,y,abs_tol=1e-12) for x,y in zip(a['ci95_relative_diff'],b['ci95_relative_diff']))

def test_ties_are_distinct_from_positive_and_negative_predictions():
    assert [audit.sign(v) for v in [.9,1.,1.1]]==[-1,0,1]

def test_exact_bound_matches_closed_form_when_no_losses():
    assert math.isclose(audit.upper_binomial(0,20),1-.1**(1/20),abs_tol=1e-12)
    assert audit.upper_binomial(20,20)==1
