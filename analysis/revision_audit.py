#!/usr/bin/env python3
"""2026-09-04 corrections; preserves every frozen file. See paper/revision/ANALYSIS_PLAN.md."""
from __future__ import annotations
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import math
import random
import statistics as st
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'analysis'))
import stats
import e2_tests as legacy

def corrected_cost(pairs):
    rel = [(p['cost_C'] - p['cost_B']) / p['cost_B'] for p in pairs]
    lo, hi = stats.bca_ci(rel)
    p = stats.paired_permutation_p(rel)
    med = st.median(rel)
    return dict(n=len(rel), median_relative_diff=med, mean_relative_diff=st.mean(rel),
                p_value=p, ci95_relative_diff=[lo,hi], significant=p < .05 and not lo <= 0 <= hi,
                substantial_reduction=med <= -.20)

def corrected_quality(pairs):
    differences = [100.0*(p['accepted_C']-p['accepted_B']) for p in pairs]
    lower = stats.bca_one_sided(differences, statistic=st.mean, conf=.90, side='lower')
    return dict(n=len(pairs), pass_B=sum(p['accepted_B'] for p in pairs),
                pass_C=sum(p['accepted_C'] for p in pairs), diff_pp=st.mean(differences),
                ci90_lower_pp=lower, non_inferior=lower > -10)

def sign(x):
    return (x > 1) - (x < 1)

def upper_binomial(k, n, alpha=.10):
    """One-sided exact Clopper--Pearson upper limit, via monotone bisection."""
    if k == n: return 1.0
    left, right = 0.0, 1.0
    for _ in range(100):
        p=(left+right)/2
        cdf=sum(math.comb(n,j)*p**j*(1-p)**(n-j) for j in range(k+1))
        if cdf > alpha: left=p
        else: right=p
    return (left+right)/2

def stratified_interval(pairs):
    by=defaultdict(list)
    for p in pairs: by[p['spec']].append((p['cost_C']-p['cost_B'])/p['cost_B'])
    rng=random.Random(stats.SEED)
    boots=[]
    for _ in range(stats.N_RESAMPLES):
        sample=[]
        for s in sorted(by):
            v=by[s]; sample.extend(v[rng.randrange(len(v))] for _ in v)
        boots.append(st.median(sample))
    boots.sort()
    # Explicit linear interpolation, matching the conventional percentile definition.
    def q(p):
        x=p*(len(boots)-1); a=int(x); b=min(a+1,len(boots)-1)
        return boots[a]+(x-a)*(boots[b]-boots[a])
    return [q(.025),q(.975)]

def main():
    outdir=ROOT/'paper/revision'; outdir.mkdir(exist_ok=True,parents=True)
    manifest=json.loads((ROOT/'analysis/frozen_manifest.json').read_text())
    mismatches=[p for p,h in manifest['files'].items()
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    assert not mismatches, mismatches
    saved=json.loads((ROOT/'analysis/e1_dataset_main.json').read_text())
    original=json.loads((ROOT/'analysis/e2_results_main.json').read_text())
    # Execute the original scripts against read-only input links, writing only into temp.
    log=io.StringIO()
    with tempfile.TemporaryDirectory(prefix='paper-reproduce-') as name:
        temp=Path(name); (temp/'analysis').mkdir()
        for target in ['runs','run_ledger_main.csv']:
            (temp/target).symlink_to(ROOT/target)
        (temp/'analysis/model_predictions.json').symlink_to(ROOT/'analysis/model_predictions.json')
        spec=importlib.util.spec_from_file_location('original_e1', ROOT/'analysis/e1_aggregate.py')
        e1=importlib.util.module_from_spec(spec); spec.loader.exec_module(e1); e1.ROOT=temp
        oldargs=sys.argv[:]; oldroot=legacy.ROOT
        try:
            sys.argv=['e1_aggregate.py','main']
            with contextlib.redirect_stdout(log): assert e1.main()==0
            regenerated=json.loads((temp/'analysis/e1_dataset_main.json').read_text())
            assert regenerated==saved, 'E1 JSON changed'
            sys.argv=['e2_tests.py','main','--acknowledge-stop','A-6']; legacy.ROOT=temp
            with contextlib.redirect_stdout(log): assert legacy.main()==0
            rerun=json.loads((temp/'analysis/e2_results_main.json').read_text())
            assert rerun==original, 'E2 JSON changed'
        finally: sys.argv=oldargs; legacy.ROOT=oldroot
    pairs=saved['pairs']; by=defaultdict(list)
    cost=corrected_cost(pairs); quality=corrected_quality(pairs)
    timing=legacy.h2_time(pairs)
    rows=[]; pair_timing=[]; usage_diffs=[]
    for p in pairs:
        by[p['spec']].append(p)
        t={}
        for arm in ['B','C']:
            d=json.loads((ROOT/f"runs/main/{p['spec']}/{arm}/rep{p['rep']}/run.json").read_text())
            end=datetime.fromisoformat(d['iso']).timestamp()
            t[arm]=(end-float(d['wall_s']),end)
            actual=d.get('usage_actual') or {}
            # Dataset costs are the ledger's six-decimal presentation of run costs.
            if 'cost_usd' in actual:
                usage_diffs.append(abs(p[f'cost_{arm}']-actual['cost_usd']))
        first,second=sorted(t,key=lambda a:t[a][0])
        pair_timing.append(dict(spec=p['spec'],rep=p['rep'],first=first,
                               gap_min=(t[second][0]-t[first][1])/60,
                               planned_first='B' if p['rep']%2 else 'C'))
    preds=json.loads((ROOT/'analysis/model_predictions.json').read_text())
    for s,ps in sorted(by.items()):
        rel=[(p['cost_C']-p['cost_B'])/p['cost_B'] for p in ps]
        cb=sum(p['cost_B'] for p in ps); cc=sum(p['cost_C'] for p in ps)
        r=cc/cb; rh=preds['specs'][s]['prediction']['r_hat']
        rows.append(dict(spec=s,n=len(ps),cost_B_median=st.median(p['cost_B'] for p in ps),
                         cost_C_median=st.median(p['cost_C'] for p in ps),
                         median_relative_diff=st.median(rel),cheaper=sum(v<0 for v in rel),
                         r_observed=r,r_hat=rh,relative_error=(r-rh)/rh,
                         legacy_sign_match=(r>1)==(rh>1),strict_sign_match=sign(r)==sign(rh)))
    distant={(p['spec'],p['rep']) for p in pair_timing if p['gap_min']>=10}
    no_ct=[p for p in pairs if p['spec']!='ct_library']
    near=[p for p in pairs if (p['spec'],p['rep']) not in distant]
    losses=sum(p['accepted_B']==1 and p['accepted_C']==0 for p in pairs)
    cb=sum(p['cost_B'] for p in pairs); cc=sum(p['cost_C'] for p in pairs)
    output=dict(schema='paper-revision/v1',date='2026-09-04',acknowledge_stop='A-6',
                frozen_file_count=len(manifest['files']),frozen_unchanged=True,
                e1_reproduced=True,e2_reproduced=True,
                corrections=dict(H1_cost=cost,H3_quality=quality),H2_time=timing,
                H4b=dict(rows=rows,within_tolerance_count=sum(abs(r['relative_error'])<=.25 for r in rows),
                         overprediction_count=sum(r['r_hat']>r['r_observed'] for r in rows),
                         legacy_mismatches=[r['spec'] for r in rows if not r['legacy_sign_match']],
                         strict_mismatches=[r['spec'] for r in rows if not r['strict_sign_match']],verdict=False),
                totals=dict(B=cb,C=cc,relative_difference=cc/cb-1,cheaper_pairs=sum(p['cost_C']<p['cost_B'] for p in pairs),
                            max_ledger_run_rounding_difference=max(usage_diffs) if usage_diffs else None),
                supplementary=dict(fixed_spec_percentile_ci95=stratified_interval(pairs),
                                   conservative_exact_quality_lower_pp=-100*upper_binomial(losses,len(pairs)),
                                   no_ct=corrected_cost(no_ct),near_pairs=corrected_cost(near)),
                timing=dict(first_counts=dict(Counter(t['first'] for t in pair_timing)),
                            plan_mismatch_count=sum(t['first']!=t['planned_first'] for t in pair_timing),
                            gap_min=min(t['gap_min'] for t in pair_timing),
                            gap_median=st.median(t['gap_min'] for t in pair_timing),
                            gap_max=max(t['gap_min'] for t in pair_timing),distant_n=len(distant),pairs=pair_timing),
                central_claim_supported=bool(cost['significant'] and cost['substantial_reduction'] and timing['non_inferior'] and quality['non_inferior']))
    (outdir/'results.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    (outdir/'legacy_reproduction.txt').write_text(log.getvalue())
    summary={k:v for k,v in output.items() if k not in ['timing','H4b']}
    summary['H4b']={k:v for k,v in output['H4b'].items() if k!='rows'}
    summary['timing']={k:v for k,v in output['timing'].items() if k!='pairs'}
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
