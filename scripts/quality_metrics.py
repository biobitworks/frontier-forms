"""Binary classification diagnostic metrics with explicit denominator checks."""
def confusion(labels,scores,threshold=0.5):
    if len(labels)!=len(scores) or not labels: raise ValueError("misaligned or empty")
    if any(y not in (0,1) for y in labels): raise ValueError("nonbinary labels")
    if any(not isinstance(s,(float,int)) or s<0 or s>1 for s in scores): raise ValueError("invalid score")
    tn=tp=fp=fn=0
    for y,s in zip(labels,scores):
        pred=int(s>=threshold)
        if y==1 and pred: tp+=1
        elif y==0 and pred: fp+=1
        elif y==1: fn+=1
        else: tn+=1
    return dict(TN=tn,TP=tp,FP=fp,FN=fn,
        FPR=fp/(fp+tn) if fp+tn else None,
        FDR=fp/(fp+tp) if fp+tp else None,
        TPR=tp/(tp+fn) if tp+fn else None,
        precision=tp/(tp+fp) if tp+fp else None)
def auroc(labels,scores):
    if len(labels)!=len(scores): raise ValueError("misaligned")
    pos=[s for y,s in zip(labels,scores) if y==1]
    neg=[s for y,s in zip(labels,scores) if y==0]
    if not pos or not neg: return None
    return sum((s>t)+0.5*(s==t) for s in pos for t in neg)/(len(pos)*len(neg))
def holm(pvalues):
    order=sorted(range(len(pvalues)),key=lambda i:pvalues[i])
    result=[None]*len(pvalues);prior=0.
    for rank,i in enumerate(order):
        prior=max(prior,min(1.,pvalues[i]*(len(pvalues)-rank)))
        result[i]=prior
    return result
