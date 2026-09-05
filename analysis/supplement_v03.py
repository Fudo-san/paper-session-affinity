#!/usr/bin/env python3
"""Post-hoc v0.3 descriptions; no changes to frozen predictions or primary tests."""
from pathlib import Path
from collections import defaultdict, Counter
import hashlib
import json
import math
import statistics as st
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'analysis'))
import stats

CONTROLS={'w_two_files','s17_w_two_files'}
RATES={'input_tokens':3.0,'output_tokens':15.0,'cache_read_tokens':.30,'cache_creation_tokens':3.75}
KEYS=tuple(RATES)+('cost_usd',)

def sign_test(values):
    minus=sum(x<0 for x in values);plus=sum(x>0 for x in values);n=minus+plus
    p=min(1.0,2*sum(math.comb(n,j) for j in range(min(minus,plus)+1))/2**n) if n else 1.0
    return dict(negative=minus,positive=plus,ties=len(values)-n,p_two_sided=p)

def summary(pairs):
    rel=[(p['cost_C']-p['cost_B'])/p['cost_B'] for p in pairs]
    dollars=[p['cost_C']-p['cost_B'] for p in pairs]
    return dict(n=len(pairs),median=st.median(rel),mean=st.mean(rel),relative_sum=sum(rel),
                ci95=list(stats.bca_ci(rel)),min=min(rel),max=max(rel),
                median_usd=st.median(dollars),mean_usd=st.mean(dollars),
                B_median=st.median(p['cost_B'] for p in pairs),sign=sign_test(rel))

def totals(us):
    us=list(us)
    return {k:sum(u.get(k,0) or 0 for u in us) for k in KEYS}

def accounting(b,c):
    parts={k:{'tokens_B':b[k],'tokens_C':c[k],'tokens_delta':c[k]-b[k],
              'usd_B':b[k]*p/1e6,'usd_C':c[k]*p/1e6,'usd_delta':(c[k]-b[k])*p/1e6} for k,p in RATES.items()}
    sb=sum(v['usd_B'] for v in parts.values());sc=sum(v['usd_C'] for v in parts.values())
    delta=c['cost_usd']-b['cost_usd']
    parts['residual']={'usd_B':b['cost_usd']-sb,'usd_C':c['cost_usd']-sc,
                       'usd_delta':delta-(sc-sb)}
    assert math.isclose(sum(v['usd_delta'] for v in parts.values()),delta,abs_tol=1e-10)
    return dict(B=b,C=c,parts=parts,reported_delta=delta,reported_ratio=c['cost_usd']/b['cost_usd'],
                standardized_B=sb,standardized_C=sc,standardized_delta=sc-sb)

def matching_suffix(calls,usage):
    """Diagnostic only: matching nonnegative terminal sums; ambiguous => do not select."""
    matches=[i for i in range(len(calls)) if all(math.isclose(totals(calls[i:])[k],usage[k],rel_tol=0,abs_tol=1e-7) for k in KEYS)]
    return matches[0] if len(matches)==1 else None

def main():
    out=ROOT/'paper/revision/v0.3';out.mkdir(exist_ok=True,parents=True)
    manifest=json.loads((ROOT/'analysis/frozen_manifest.json').read_text())['files']
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in manifest.items())
    pairs=json.loads((ROOT/'analysis/e1_dataset_main.json').read_text())['pairs']
    v02=json.loads((ROOT/'paper/revision/results.json').read_text())
    groups={'all':pairs,'non_ct':[p for p in pairs if p['spec']!='ct_library'],
            'controls':[p for p in pairs if p['spec'] in CONTROLS],
            'active':[p for p in pairs if p['spec'] not in CONTROLS]}
    specs={s:summary([p for p in pairs if p['spec']==s]) for s in sorted({p['spec'] for p in pairs})}
    results={'analysis_version':'0.3-post-hoc','frozen_files_verified':len(manifest),'rates_usd_per_million':RATES,
             'groups':{s:summary(ps) for s,ps in groups.items()},'specs':specs}
    active=[r for r in v02['H4b']['rows'] if r['spec'] not in CONTROLS]
    results['active_model']={'n':len(active),'within25':sum(abs(r['relative_error'])<=.25 for r in active),
                             'overpredicted':sum(r['r_hat']>r['r_observed'] for r in active),'rows':active}
    runs=defaultdict(list);calls_by=defaultdict(list);matches=[];unmatched=[];allcount=0
    for p in sorted((ROOT/'runs/main').glob('**/run.json')):
        r=json.loads(p.read_text());runs[(r['spec'],r['arm'])].append(r)
        cs=[json.loads(l) for l in p.with_name('calls.jsonl').read_text().splitlines() if l.strip()]
        calls_by[(r['spec'],r['arm'])].extend(cs);allcount+=len(cs)
        i=matching_suffix(cs,r['usage_actual'])
        if i is None:unmatched.append(str(p.relative_to(ROOT)))
        else:matches.append({'run':r['run_id'],'prefix_calls':i,'suffix_calls':len(cs)-i})
        if r['spec']=='ct_library':assert i==0 and len(cs)==3
        # Do not select rows by matching total cost alone or drop the unmatched run.
    for p in pairs:
        for a in ['B','C']:
            r=next(r for r in runs[(p['spec'],a)] if r['rep']==p['rep'])
            assert math.isclose(p['cost_'+a],r['usage_actual']['cost_usd'],abs_tol=1e-10)
    results['log_audit']={'run_count':sum(map(len,runs.values())),'all_calls':allcount,'matched_suffix_runs':len(matches),
                          'prefixes':[x for x in matches if x['prefix_calls']], 'unmatched_runs':unmatched}
    results['accounting']={s:accounting(totals(r['usage_actual'] for r in runs[(s,'B')]),
                                      totals(r['usage_actual'] for r in runs[(s,'C')])) for s in specs}
    results['accounting']['all']=accounting(totals(r['usage_actual'] for (s,a),rs in runs.items() if a=='B' for r in rs),
                                          totals(r['usage_actual'] for (s,a),rs in runs.items() if a=='C' for r in rs))
    results['ct_tasks']={}
    for task in sorted({c['task_id'] for c in calls_by[('ct_library','B')]}):
        arms={a:[c for c in calls_by[('ct_library',a)] if c['task_id']==task] for a in ['B','C']}
        assert all(len(cs)==14 for cs in arms.values())
        record=accounting(totals(arms['B']),totals(arms['C']))
        record['activity']={a:{'calls':len(cs),'resumed':sum(c['resumed'] for c in cs),
                    'reported_turns':sum(c['num_turns'] for c in cs),
                    'recorded_turn_rows':sum(len(c['turns']) for c in cs),
                    'partial_output_sum':sum(t['output_tokens_partial'] for c in cs for t in c['turns'])} for a,cs in arms.items()}
        results['ct_tasks'][task]=record
    results['ct_activity']={a:{'calls':len(calls_by[('ct_library',a)]),
                    'reported_turns':sum(c['num_turns'] for c in calls_by[('ct_library',a)]),
                    'recorded_turn_rows':sum(len(c['turns']) for c in calls_by[('ct_library',a)]),
                    'mixed_model_calls':sum(len(c['models_used'])>1 for c in calls_by[('ct_library',a)]),
                    'input_detail_minus_result':{k:sum(sum(t[k] for t in c['turns'])-c[k] for c in calls_by[('ct_library',a)]) for k in RATES if k!='output_tokens'}} for a in ['B','C']}
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:results[k] for k in ['groups','active_model','ct_activity','log_audit']},ensure_ascii=False,indent=2))
    print('CT accounting:',json.dumps(results['accounting']['ct_library'],indent=2))
if __name__=='__main__':main()
