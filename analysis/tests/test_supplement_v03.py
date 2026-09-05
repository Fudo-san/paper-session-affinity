"""Synthetic checks for new descriptive analyses and accounting boundaries."""
import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import supplement_v03 as s

def test_sign_test_handles_ties_and_exact_tail():
    assert s.sign_test([1]*14)['p_two_sided']==2/2**14
    assert s.sign_test([-1,1,0])=={'negative':1,'positive':1,'ties':1,'p_two_sided':1.0}

def test_large_minority_changes_mean_but_not_median_sign():
    import statistics as st
    values=[-1]*6+[100]*4
    assert st.mean(values)>0 and st.median(values)<0
    assert s.sign_test(values)['negative']==6

def test_cost_breakdown_keeps_unexplained_residual():
    b={k:100 for k in s.RATES};b['cost_usd']=1
    c={k:200 for k in s.RATES};c['cost_usd']=1.1
    r=s.accounting(b,c)
    assert abs(r['parts']['residual']['usd_delta'])>.09
    assert math.isclose(sum(v['usd_delta'] for v in r['parts'].values()),.1)

def test_suffix_requires_all_usage_fields_and_rejects_ambiguity():
    c={k:2 for k in s.KEYS};zero={k:0 for k in s.KEYS}
    assert s.matching_suffix([c,c],c)==1
    assert s.matching_suffix([zero,c],c) is None
    wrong=dict(c,output_tokens=9)
    assert s.matching_suffix([wrong],c) is None

def test_totals_accepts_iterator_without_consuming_after_first_field():
    values=[{k:1 for k in s.KEYS},{k:2 for k in s.KEYS}]
    assert s.totals(iter(values))=={k:3 for k in s.KEYS}
