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
    # Sensitivity, not a refit: put the observed carry into the frozen formula and see where it lands.
    def ct_r_hat(scale):
        cal_={t['task_id']:t for t in preds['specs']['ct_library']['calibration']}
        lane_=preds['specs']['ct_library']['lanes']['lane-CT-A']
        ar,aw,unit=preds['alpha_r'],preds['alpha_w'],RATES['input_tokens']/1e6
        tb=tc=0.0;h=None
        for pos,tid in enumerate(lane_):
            t=cal_[tid];rho=1 if pos else 0;cb=t['cost_usd']
            cc=cb if h is None else (cb-t['E_tokens']*ar*unit
                +(rho*aw+(max(1,t['K']-t['K_E'])-rho)*ar)*h*scale.get(tid,1.0)*unit)
            tb+=cb;tc+=cc;h=t['peak_context']
        return tc/tb

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
    obs_ratio=results['accounting']['ct_library']['reported_ratio']
    frac={r['task']:r['observed_over_assumed'] for r in results['carry_check']['rows'] if 'observed_over_assumed' in r}
    frozen,swapped=ct_r_hat({}),ct_r_hat(frac)
    results['carry_check']['substitution']={'r_observed':obs_ratio,'r_hat_frozen':frozen,'r_hat_observed_carry':swapped,
        'relative_error_frozen':(obs_ratio-frozen)/frozen,'relative_error_observed_carry':(obs_ratio-swapped)/swapped,
        'note':'Substituting the observed carry into the frozen formula. Not a recalibration; the frozen prediction stands.'}

    # The auxiliary model, priced. calls.jsonl kept only model names, but the probes stored
    # the raw CLI result, whose modelUsage carries per-model cost and tokens.
    aux=[]
    for pf in sorted((ROOT/'probes').glob('*.jsonl')):
        for line in pf.read_text().splitlines():
            if not line.strip():continue
            d=json.loads(line);r=d.get('raw')
            if not isinstance(r,dict):continue
            mu=r.get('modelUsage') or {}
            if d.get('resumed') or d.get('resume') or d.get('model_flag')=='haiku':continue
            h=[v for k,v in mu.items() if 'haiku' in k];m=[v for k,v in mu.items() if 'haiku' not in k]
            if not(h and m):continue
            u=r.get('usage') or {}
            aux.append({'payload_chars':d.get('payload_chars'),'cost':h[0]['costUSD'],
                'input':h[0]['inputTokens'],'output':h[0]['outputTokens'],
                'cache_read':h[0].get('cacheReadInputTokens',0),'cache_creation':h[0].get('cacheCreationInputTokens',0),
                'usage_equals_main':(u.get('input_tokens')==m[0]['inputTokens'] and u.get('output_tokens')==m[0]['outputTokens']
                    and u.get('cache_read_input_tokens')==m[0].get('cacheReadInputTokens')
                    and u.get('cache_creation_input_tokens')==m[0].get('cacheCreationInputTokens'))})
    costs=[a['cost'] for a in aux];ins=[a['input'] for a in aux]
    results['aux_model']={'n':len(aux),'cost_median':st.median(costs),'cost_min':min(costs),'cost_max':max(costs),
        'input_median':st.median(ins),'input_min':min(ins),'input_max':max(ins),
        'output_median':st.median(a['output'] for a in aux),
        'cache_read_max':max(a['cache_read'] for a in aux),'cache_creation_max':max(a['cache_creation'] for a in aux),
        'payload_chars_span':[min(a['payload_chars'] for a in aux if a['payload_chars']),
                              max(a['payload_chars'] for a in aux if a['payload_chars'])],
        'usage_excludes_aux':sum(a['usage_equals_aux'] if False else a['usage_equals_main'] for a in aux),
        'note':'Probe records only; the probes ran CLI 2.1.220 and the main experiment 2.1.247.'}

    # Two readings of that call, priced onto the main experiment.
    fresh=defaultdict(lambda:defaultdict(int))
    for (s_,a),cs in calls_by.items():
        for c in cs:
            if not c['resumed']: fresh[(s_,c['rep'])][a]+=1
    AUX=results['aux_model']['cost_median']
    SUB=results['aux_model']['input_median']*RATES['input_tokens']/1e6
    def shifted(delta):
        v=[]
        for p_ in pairs:
            nb,nc=fresh[(p_['spec'],p_['rep'])]['B'],fresh[(p_['spec'],p_['rep'])]['C']
            b,c=p_['cost_B']+nb*delta,p_['cost_C']+nc*delta
            v.append((c-b)/b)
        return v
    scen={'observed':0.0,'aux_removed':-AUX,'aux_done_by_main_model':SUB-AUX}
    results['aux_sensitivity']={'aux_cost_per_fresh_call':AUX,'main_model_cost_for_same_tokens':SUB,
        'fresh_calls':{a:sum(f[a] for f in fresh.values()) for a in ('B','C')},
        'scenarios':{k:{'median':st.median(shifted(d)),'ci95':list(stats.bca_ci(shifted(d))),
                        'cheaper':sum(x<0 for x in shifted(d))} for k,d in scen.items()},
        'note':'Bounds, not an identification. Which reading holds is not decidable from these logs.'}

    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:results[k] for k in ['groups','active_model','ct_activity','log_audit']},ensure_ascii=False,indent=2))
    print('CT accounting:',json.dumps(results['accounting']['ct_library'],indent=2))
    print('model mix:',json.dumps(results['model_mix']['by_reuse'],ensure_ascii=False))
    print('carry check:',json.dumps(results['carry_check']['rows'],ensure_ascii=False))
    print('carry substitution:',json.dumps(results['carry_check']['substitution'],ensure_ascii=False))
if __name__=='__main__':main()
