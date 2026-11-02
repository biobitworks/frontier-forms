"""Statistical admission for paired binary correctness; only controlled held-out results warrant promotion."""
from __future__ import annotations
from collections import Counter,defaultdict
import math,random

def paired_table(records):
    # 0=baseline only; 1=challenger only. Exact pairing is mandatory.
    if len({x['case_digest_sha256'] for x in records})!=len(records):raise ValueError('DUPLICATE_ROW')
    both=sum(bool(x['baseline_correct']) and bool(x['challenger_correct']) for x in records)
    a=sum(bool(x['baseline_correct']) and not bool(x['challenger_correct']) for x in records)
    b=sum(not bool(x['baseline_correct']) and bool(x['challenger_correct']) for x in records)
    neither=len(records)-both-a-b
    return {'both_correct':both,'baseline_only':a,'challenger_only':b,'both_wrong':neither,'n':len(records)}
def exact_mcnemar(a,b):
    """Two-sided exact binomial McNemar; H0 discordances symmetric; NOT a t-test."""
    n=a+b
    return min(1.0,2*sum(math.comb(n,k) for k in range(min(a,b)+1))/2**n) if n else 1.
def paired_bootstrap(records,reps=10000,seed=20261102,alpha=0.05,stratified=True):
    if not records:raise ValueError('EMPTY')
    groups=defaultdict(list)
    for row in records: groups[row['task'] if stratified else 'all'].append(row)
    rng=random.Random(seed)
    arr=[]
    n=len(records)
    for _ in range(reps):
        diff=0
        for group in groups.values():
            for __ in range(len(group)):
                x=rng.choice(group)
                diff+=int(bool(x['challenger_correct']))-int(bool(x['baseline_correct']))
        arr.append(diff/n)
    arr.sort()
    return [arr[max(0,int(alpha/2*reps))],arr[min(reps-1,int((1-alpha/2)*reps)-1)]]
def admit(records,phase='discovery',reps=10000,seed=20261102,alpha=.05):
    t=paired_table(records)
    ci=paired_bootstrap(records,reps=reps,seed=seed)
    p=exact_mcnemar(t['baseline_only'],t['challenger_only'])
    d=(t['challenger_only']-t['baseline_only'])/t['n']
    # Significance is not sufficient: must be matched heldout + positive direction
    # and a separate untouched replication set.
    return {'n':t['n'],'table':t,'p_mcnemar_exact_two_sided':p,
      'ci_delta_bootstrap_stratified_95':ci,'delta':d,'phase':phase,
      'alpha':alpha,'bootstrap_reps':reps,'bootstrap_seed':seed,
      'mcnemar_positive_gate':p<alpha and d>0,
      'bootstrap_positive_gate':ci[0]>0,
      'replication_gate':'NOT_TESTED',
      'promotion':'BLOCKED_REPLICATION_UNVERIFIED' if p<alpha and ci[0]>0 and phase=='heldout' else 'NO_SUPERIORITY_CLAIM'}
def binary_confusion(rows, positive='A'):
    tp=sum(x['gold']==positive and x['pred']==positive for x in rows)
    fp=sum(x['gold']!=positive and x['pred']==positive for x in rows)
    tn=sum(x['gold']!=positive and x['pred']!=positive for x in rows)
    fn=sum(x['gold']==positive and x['pred']!=positive for x in rows)
    div=lambda n,d:(n/d if d else None)
    return {'positive_label':positive,'TP':tp,'FP':fp,'TN':tn,'FN':fn,
      'FPR':div(fp,fp+tn),'FDR':div(fp,tp+fp),'TPR':div(tp,tp+fn),
      'precision':div(tp,tp+fp),
      'AUROC':'NOT_COMPUTED_NO_CONTINUOUS_SCORES',
      'note':'A is an arbitrary benchmark answer token, not a clinical disease-positive label.'}
