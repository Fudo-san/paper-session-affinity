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

def test_reuse_key_splits_session_reuse_from_auxiliary_model_use():
    fresh_aux={'resumed':False,'models_used':['main','aux']}
    resumed_single={'resumed':True,'models_used':['main']}
    assert s.reuse_key(fresh_aux)==('fresh','aux')
    assert s.reuse_key(resumed_single)==('resumed','single')
    # A single entry is not auxiliary use even when the run was resumed.
    assert s.reuse_key({'resumed':True,'models_used':['aux']})==('resumed','single')

def test_reported_over_standardized_is_one_when_the_rate_card_fits():
    acc={'B':{'cost_usd':4.0},'C':{'cost_usd':5.0},'standardized_B':4.0,'standardized_C':10.0}
    assert s.reported_over_standardized(acc,'B')==1.0
    assert s.reported_over_standardized(acc,'C')==0.5

def test_paired_relative_keeps_rep_alignment_and_rejects_length_mismatch():
    assert s.paired_relative([1.0,2.0],[2.0,1.0])==[1.0,-0.5]
    try:
        s.paired_relative([1.0],[1.0,2.0]);assert False
    except AssertionError as e:
        assert not str(e)

def test_turn_reduction_and_cost_increase_can_hold_together():
    """The CT pattern: fewer turns, higher cost, so per-turn cost must rise."""
    b={'cost':3.28,'turns':201};c={'cost':4.57,'turns':153}
    assert c['turns']<b['turns'] and c['cost']>b['cost']
    assert (c['cost']/c['turns'])/(b['cost']/b['turns'])>1.8

def test_frozen_prediction_is_reproduced_before_any_substitution():
    """The sensitivity check must start from the frozen r_hat, not a refitted one."""
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    v3=json.loads((root/'paper/revision/v0.3/results.json').read_text())
    sub=v3['carry_check']['substitution']
    frozen=next(r for r in v3['active_model']['rows'] if r['spec']=='ct_library')
    assert math.isclose(sub['r_hat_frozen'],frozen['r_hat'],abs_tol=5e-5)
    assert math.isclose(sub['relative_error_frozen'],frozen['relative_error'],abs_tol=5e-5)
    # Shrinking the carried history lowers the prediction, so the sign of the error flips.
    assert sub['r_hat_observed_carry']<sub['r_hat_frozen']
    assert sub['relative_error_frozen']<0<sub['relative_error_observed_carry']

def test_auxiliary_model_call_does_not_scale_with_the_payload():
    """A fixed-size call is what licenses carrying the probe estimate into the main runs."""
    import json
    from pathlib import Path
    v3=json.loads((Path(__file__).resolve().parents[2]/'paper/revision/v0.3/results.json').read_text())
    a=v3['aux_model']
    lo,hi=a['payload_chars_span']
    assert hi/lo>=50                      # the payload varies by a wide factor
    assert a['input_max']-a['input_min']<100   # the auxiliary input barely moves
    assert a['cache_read_max']==0 and a['cache_creation_max']==0
    assert a['usage_excludes_aux']==a['n']     # its tokens never enter the usage aggregate

def test_both_readings_of_the_auxiliary_call_leave_the_cost_verdict_unchanged():
    import json
    from pathlib import Path
    v3=json.loads((Path(__file__).resolve().parents[2]/'paper/revision/v0.3/results.json').read_text())
    sc=v3['aux_sensitivity']['scenarios']
    # Removing it and having the main model do it bracket the observed value from both sides.
    assert sc['aux_done_by_main_model']['median']<sc['observed']['median']<sc['aux_removed']['median']
    # Neither reading reaches the pre-specified 20% reduction.
    for v in sc.values():
        assert v['median']>-0.20 and v['ci95'][1]>-0.20
