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

def reuse_key(call):
    """How one call record is classified: session reuse x auxiliary-model use."""
    return ('resumed' if call['resumed'] else 'fresh',
            'aux' if len(call['models_used'])>1 else 'single')

def reported_over_standardized(acc,arm):
    """Reported cost divided by the fixed-rate conversion. 1.0 means the rate card fits."""
    return acc[arm]['cost_usd']/acc['standardized_'+arm]

def paired_relative(b,c):
    """Per-rep relative differences for two aligned sequences."""
    assert len(b)==len(c)
    return [(y-x)/x for x,y in zip(b,c)]

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
            'active':[p for p in pairs if p['spec'] not in CONTROLS],
            # Continuation actually happened and the shape is not a direct-conflict control.
            'active_non_ct':[p for p in pairs if p['spec'] not in CONTROLS and p['spec']!='ct_library']}
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
    # Auxiliary-model use vs session reuse. Counts call records, re-executions included.
    mix=Counter();mix_spec=defaultdict(Counter)
    for (s_,a),cs in calls_by.items():
        for c in cs:
            k=reuse_key(c)
            mix[k]+=1;mix_spec[(s_,a)][k]+=1
    results['model_mix']={'calls':sum(mix.values()),
        'by_reuse':{r:{m:mix[(r,m)] for m in ('aux','single')} for r in ('fresh','resumed')},
        'by_spec_arm':{f'{s_}|{a}':{f'{r}_{m}':n for (r,m),n in sorted(c.items())} for (s_,a),c in sorted(mix_spec.items())},
        'models_seen':sorted({m for cs in calls_by.values() for c in cs for m in c['models_used']})}

    # Reported cost over fixed-rate conversion. Near-constant => the residual scales, not adds.
    results['residual_ratio']={s_:{a:reported_over_standardized(results['accounting'][s_],a)
                                   for a in ('B','C')} for s_ in list(specs)+['all']}

    # Per-rep paired differences inside CT, and the context each task actually carried.
    preds=json.loads((ROOT/'analysis/model_predictions.json').read_text())
    for task,record in results['ct_tasks'].items():
        by={a:{c['rep']:c for c in calls_by[('ct_library',a)] if c['task_id']==task} for a in ('B','C')}
        reps=sorted(set(by['B'])&set(by['C']));assert len(reps)==14
        rel=paired_relative([by['B'][r]['cost_usd'] for r in reps],[by['C'][r]['cost_usd'] for r in reps])
        dturn=[by['C'][r]['num_turns']-by['B'][r]['num_turns'] for r in reps]
        record['paired']={'n':len(reps),'median_relative_diff':st.median(rel),'ci95':list(stats.bca_ci(rel)),
                          'sign':sign_test(rel),'median_turn_delta':st.median(dturn),'turn_sign':sign_test(dturn)}
        record['context']={a:st.median(by[a][r]['peak_context_tokens'] for r in reps) for a in ('B','C')}
        record['per_turn_usd']={a:record[a]['cost_usd']/record['activity'][a]['reported_turns'] for a in ('B','C')}
        record['per_turn_ratio']=record['per_turn_usd']['C']/record['per_turn_usd']['B']
    lane=preds['specs']['ct_library']['lanes']['lane-CT-A']
    cal={t['task_id']:t for t in preds['specs']['ct_library']['calibration']}
    results['carry_check']={'lane':lane,'note':'peak context is a maximum, not the per-turn mean; the first task carries nothing.','rows':[]}
    for i,task in enumerate(lane):
        ctx=results['ct_tasks'][task]['context'];grow=ctx['C']-ctx['B']
        row={'task':task,'context_B':ctx['B'],'context_C':ctx['C'],'observed_growth':grow,'continued':i>0}
        if i:
            row['assumed_carry']=cal[lane[i-1]]['peak_context']
            row['observed_over_assumed']=grow/row['assumed_carry']
        results['carry_check']['rows'].append(row)

    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:results[k] for k in ['groups','active_model','ct_activity','log_audit']},ensure_ascii=False,indent=2))
    print('CT accounting:',json.dumps(results['accounting']['ct_library'],indent=2))
    print('model mix:',json.dumps(results['model_mix']['by_reuse'],ensure_ascii=False))
    print('carry check:',json.dumps(results['carry_check']['rows'],ensure_ascii=False))
if __name__=='__main__':main()
