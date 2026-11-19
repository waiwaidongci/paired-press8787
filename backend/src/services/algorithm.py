"""三项加性效应（纸样＋测量员＋仪器）的可估性判定与限额内补测规划。

模型：y = 纸样效应 + 测量员效应 + 仪器效应 + 误差（无交互）。
两两差异可辨（可估）当且仅当对比向量落在设计矩阵行空间内；
判定全部使用有理数精确计算，与浮点误差无关。
补测规划在 ≤24 组候选中做精确子集搜索：先最大化可辨的
测量员/仪器两两差异数，相同则取测量次数更少者，每个组合至多一次。
该搜索是 NP 难的，24 组上限保证有界。可辨差异数目标由有理数搜索
精确求得；最少测量次数在两个大素数有限域上独立搜索并互相印证，
最终方案的可辨性经有理数复核，任何不一致都回退到全程有理数搜索，
报告结果与浮点误差无关。
"""
import math
from fractions import Fraction as F
import numpy as np

_PRIMES=(2**31-1,2**61-1)

# ---------- 精确有理线性代数 ----------

def _rref(rows,d):
    a=[[F(x) for x in row] for row in rows]
    a=[row for row in a if any(row)]
    pivots=[];r=0
    for c in range(d):
        if r>=len(a): break
        piv=next((i for i in range(r,len(a)) if a[i][c]),None)
        if piv is None: continue
        a[r],a[piv]=a[piv],a[r]
        inv=a[r][c]
        a[r]=[x/inv for x in a[r]]
        for i in range(len(a)):
            if i!=r and a[i][c]:
                f=a[i][c]
                a[i]=[x-f*y for x,y in zip(a[i],a[r])]
        pivots.append(c);r+=1
    return a[:r],pivots

class _Basis:
    """商空间内向量组的行最简基（有理数），支持增量加入与成员判定。"""
    __slots__=('rows','pivots')
    def __init__(self):
        self.rows=[];self.pivots=[]
    def copy(self):
        b=_Basis();b.rows=list(self.rows);b.pivots=list(self.pivots);return b
    def _reduce(self,v):
        w=list(v)
        for row,p in zip(self.rows,self.pivots):
            coeff=w[p]
            if coeff: w=[x-coeff*y for x,y in zip(w,row)]
        return w
    def add(self,v):
        w=self._reduce(v)
        p=next((j for j,x in enumerate(w) if x),None)
        if p is None: return False
        inv=w[p]
        new=tuple(x/inv for x in w)
        self.rows=[tuple(x-row[p]*y for x,y in zip(row,new)) if row[p] else row for row in self.rows]
        i=next((i for i,q in enumerate(self.pivots) if q>p),len(self.pivots))
        self.rows.insert(i,new);self.pivots.insert(i,p)
        return True
    def contains(self,v):
        return not any(self._reduce(v))

class _ModBasis:
    """有限域版本的张成基，仅用于加速搜索，不作最终判定。"""
    __slots__=('rows','pivots','p')
    def __init__(self,p):
        self.rows=[];self.pivots=[];self.p=p
    def copy(self):
        b=_ModBasis(self.p);b.rows=list(self.rows);b.pivots=list(self.pivots);return b
    def _reduce(self,v):
        w=list(v);p=self.p
        for row,j in zip(self.rows,self.pivots):
            coeff=w[j]
            if coeff: w=[(x-coeff*y)%p for x,y in zip(w,row)]
        return w
    def add(self,v):
        p=self.p
        w=self._reduce(v)
        j=next((j for j,x in enumerate(w) if x),None)
        if j is None: return False
        inv=pow(w[j],-1,p)
        new=tuple(x*inv%p for x in w)
        self.rows=[tuple((x-row[j]*y)%p for x,y in zip(row,new)) if row[j] else row for row in self.rows]
        i=next((i for i,q in enumerate(self.pivots) if q>j),len(self.pivots))
        self.rows.insert(i,new);self.pivots.insert(i,j)
        return True
    def contains(self,v):
        return not any(self._reduce(v))

def _projector(R,pivots,d):
    pset=set(pivots)
    nonpiv=[j for j in range(d) if j not in pset]
    def project(v):
        w=list(v)
        for row,p in zip(R,pivots):
            coeff=w[p]
            if coeff:
                for j in nonpiv: w[j]-=coeff*row[j]
                w[p]=F(0)
        return tuple(w[j] for j in nonpiv)
    return project

# ---------- 限额内补测规划 ----------

def _suffix_bases(vecs,basis_cls,*args):
    m=len(vecs)
    suf=[None]*(m+1);suf[m]=[]
    for i in range(m-1,-1,-1):
        b=basis_cls(*args)
        for row in suf[i+1]: b.add(row)
        b.add(vecs[i])
        suf[i]=b.rows
    return suf

def _max_pairs(vecs,keys,limits,contrasts,basis_cls,*args):
    """第一阶段：可辨差异数的最大值。"""
    m=len(vecs)
    suf=_suffix_bases(vecs,basis_cls,*args)
    best={'pairs':0}
    def dfs(i,basis,usage):
        cur=sum(1 for u in contrasts if basis.contains(u))
        if cur>best['pairs']: best['pairs']=cur
        if i==m or cur==len(contrasts): return
        ub=basis.copy()
        for row in suf[i]: ub.add(row)
        potential=sum(1 for u in contrasts if ub.contains(u))
        if potential<=best['pairs']: return
        key=keys[i]
        if usage.get(key,0)<limits.get(key,0):
            b2=basis.copy();b2.add(vecs[i])
            usage[key]=usage.get(key,0)+1
            dfs(i+1,b2,usage)
            if usage[key]==1: del usage[key]
            else: usage[key]-=1
        dfs(i+1,basis,usage)
    dfs(0,basis_cls(*args),{})
    return best['pairs']

def _min_count(vecs,keys,limits,contrasts,basis_cls,target,*args):
    """第二阶段：达到 target 项可辨差异的最少测量次数与方案。"""
    m=len(vecs)
    suf=_suffix_bases(vecs,basis_cls,*args)
    best={'count':m+1,'chosen':None}
    def dfs(i,basis,chosen,usage):
        if len(chosen)>=best['count']: return
        cur=sum(1 for u in contrasts if basis.contains(u))
        if cur==target:
            best['count']=len(chosen);best['chosen']=tuple(chosen);return
        if i==m: return
        ub=basis.copy()
        for row in suf[i]: ub.add(row)
        if sum(1 for u in contrasts if ub.contains(u))<target: return
        key=keys[i]
        if usage.get(key,0)<limits.get(key,0):
            b2=basis.copy();b2.add(vecs[i])
            usage[key]=usage.get(key,0)+1;chosen.append(i)
            dfs(i+1,b2,chosen,usage)
            chosen.pop()
            if usage[key]==1: del usage[key]
            else: usage[key]-=1
        dfs(i+1,basis,chosen,usage)
    dfs(0,basis_cls(*args),[],{})
    return best['count'],best['chosen']

def _to_mod(vec,p):
    return tuple((x.numerator*pow(x.denominator,-1,p))%p for x in vec)

def _covered_count(chosen,vecs,contrasts):
    b=_Basis()
    for i in chosen: b.add(vecs[i])
    return sum(1 for u in contrasts if b.contains(u))

def _plan(cand_vecs,cand_keys,limits,remaining):
    """返回最优补测下标（作用于 cand_vecs 的传入顺序）。

    可辨差异数目标由有理数搜索精确求得；最少测量次数在两个大素数
    有限域上独立搜索并互相印证，最终方案的可辨性经有理数复核，
    任何不一致都回退到全程有理数搜索。"""
    if not remaining or not cand_vecs: return ()
    target=_max_pairs(cand_vecs,cand_keys,limits,remaining,_Basis)
    if target==0: return ()
    counts=[]
    for p in _PRIMES:
        mv=[_to_mod(v,p) for v in cand_vecs]
        mu=[_to_mod(u,p) for u in remaining]
        t=_max_pairs(mv,cand_keys,limits,mu,_ModBasis,p)
        counts.append(_min_count(mv,cand_keys,limits,mu,_ModBasis,t,p))
    (c1,w1),(c2,_)=counts
    if c1!=c2 or w1 is None or _covered_count(w1,cand_vecs,remaining)!=target:
        _,w=_min_count(cand_vecs,cand_keys,limits,remaining,_Basis,target)
        return w or ()
    return w1

# ---------- 主入口 ----------

def calculate(snapshot,params):
    readings=snapshot.get('readings') or []
    candidates=snapshot.get('candidates') or []
    quotas=snapshot.get('quotas') or []
    if not readings: raise ValueError('空批次无法分析')
    for r in readings:
        v=r.get('values') or {}
        if any(k not in v for k in ('paper','operator','instrument','delta_e')): raise ValueError('观测字段不完整')
        x=float(v['delta_e'])
        if not math.isfinite(x) or x<0: raise ValueError('色差读数必须为有限非负数值')
    papers=sorted({str(r['values']['paper']) for r in readings}|{str(c['paper']) for c in candidates})
    operators=sorted({str(r['values']['operator']) for r in readings}|{str(c['operator']) for c in candidates})
    instruments=sorted({str(r['values']['instrument']) for r in readings}|{str(c['instrument']) for c in candidates})
    P,O,I=len(papers),len(operators),len(instruments)
    d=P+O+I
    pidx={p:i for i,p in enumerate(papers)}
    oidx={o:P+i for i,o in enumerate(operators)}
    iidx={x:P+O+i for i,x in enumerate(instruments)}
    def cell_vec(p,o,i):
        v=[F(0)]*d
        v[pidx[p]]=F(1);v[oidx[o]]=F(1);v[iidx[i]]=F(1)
        return v
    rows=[cell_vec(str(r['values']['paper']),str(r['values']['operator']),str(r['values']['instrument'])) for r in readings]
    uniq_rows=[list(x) for x in {tuple(row) for row in rows}]  # 行空间只取决于不同格子，复测行去重
    R,pivots=_rref(uniq_rows,d)
    rank=len(pivots)
    project=_projector(R,pivots,d)
    zero=tuple(F(0) for _ in range(d-rank))

    # 三类两两对比（纸样对比仅报告；测量员/仪器对比同时作为规划目标）
    def pair_entries(names,offset,label,optimize):
        out=[]
        for a in range(len(names)):
            for b in range(a+1,len(names)):
                c=[F(0)]*d;c[offset+a]=F(1);c[offset+b]=F(-1)
                u=project(c)
                out.append({'label':label,'pair':(names[a],names[b]),'vec':c,'q':u,'current':u==zero,'optimize':optimize})
        return out
    entries=pair_entries(operators,P,'测量员',True)+pair_entries(instruments,P+O,'仪器',True)+pair_entries(papers,0,'纸样',False)
    remaining=[e['q'] for e in entries if e['optimize'] and not e['current']]

    # 候选组合向量与限额；剔除不可用候选后按单兵增益排序（顺序固定，结果确定）
    limits={(str(q['operator']),str(q['instrument'])):int(q['max_count']) for q in quotas}
    usable=[]
    for idx,c in enumerate(candidates):
        key=(str(c['operator']),str(c['instrument']))
        v=project(cell_vec(str(c['paper']),key[0],key[1]))
        if v!=zero and limits.get(key,0)>0: usable.append((idx,key,v))
    order=sorted(range(len(usable)),key=lambda i:(-sum(1 for u in remaining if _contains1(usable[i][2],u)),usable[i][0]))
    s_vecs=[usable[i][2] for i in order]
    s_keys=[usable[i][1] for i in order]
    chosen_sorted=_plan(s_vecs,s_keys,limits,remaining)
    chosen=sorted(usable[order[i]][0] for i in chosen_sorted)

    # 补测后可达性
    after=_Basis()
    for i in chosen:
        key=(str(candidates[i]['operator']),str(candidates[i]['instrument']))
        after.add(project(cell_vec(str(candidates[i]['paper']),key[0],key[1])))
    for e in entries: e['after']=e['current'] or after.contains(e['q'])
    new_pairs=[e for e in entries if e['optimize'] and not e['current'] and e['after']]

    # 最小二乘估计（仅数值；可估性已由精确计算判定）
    X=np.asarray([[float(x) for x in row] for row in rows])
    y=np.asarray([float(r['values']['delta_e']) for r in readings])
    n=len(readings)
    beta,_,_,_=np.linalg.lstsq(X,y,rcond=None)
    resid=y-X@beta
    df=n-rank
    sigma2=float(resid@resid)/df if df>0 else None
    Mpinv=np.linalg.pinv(X)
    def estimate(e):
        c=np.asarray([float(x) for x in e['vec']])
        est=float(c@beta)
        se=math.sqrt(sigma2*float((Mpinv.T@c)@(Mpinv.T@c))) if sigma2 is not None else None
        return est,se

    def pair_row(e):
        est,se=estimate(e) if e['current'] else (None,None)
        return [e['label'],f"{e['pair'][0]} − {e['pair'][1]}",'是' if e['current'] else '否',
                round(est,4) if est is not None else '—',round(se,4) if se is not None else '—',
                '是' if e['after'] else '否']
    op_cur=sum(1 for e in entries if e['label']=='测量员' and e['current'])
    op_tot=sum(1 for e in entries if e['label']=='测量员')
    in_cur=sum(1 for e in entries if e['label']=='仪器' and e['current'])
    in_tot=sum(1 for e in entries if e['label']=='仪器')
    obj_tot=op_tot+in_tot
    obj_cur=op_cur+in_cur
    obj_after=sum(1 for e in entries if e['optimize'] and e['after'])

    usage={}
    for i in chosen:
        key=(str(candidates[i]['operator']),str(candidates[i]['instrument']))
        usage[key]=usage.get(key,0)+1
    quota_rows=[[o,i,usage.get((o,i),0),lim] for (o,i),lim in sorted(limits.items())]
    unquota=sum(1 for c in candidates if limits.get((str(c['operator']),str(c['instrument'])),0)<=0)

    metrics={'复测读数':n,'纸样/测量员/仪器水平数':f'{P} / {O} / {I}','设计矩阵秩':rank,'残差自由度':df,
             '测量员两两差异·当前可辨':f'{op_cur} / {op_tot}','仪器两两差异·当前可辨':f'{in_cur} / {in_tot}',
             '候选组合数':len(candidates),'补测单条数':len(chosen),'补测后新增可辨差异':len(new_pairs),
             '补测后目标差异可辨':f'{obj_after} / {obj_tot}'}
    if sigma2 is not None: metrics['残差标准差']=round(math.sqrt(sigma2),4)
    plan_rows=[[k+1,str(candidates[i]['paper']),str(candidates[i]['operator']),str(candidates[i]['instrument'])] for k,i in enumerate(chosen)]
    new_labels='、'.join(f"{e['label']}{e['pair'][0]}−{e['pair'][1]}" for e in new_pairs) or '无'
    if chosen:
        interpretation=f"当前数据可辨测量员差异 {op_cur}/{op_tot}、仪器差异 {in_cur}/{in_tot}。按补测单追加 {len(chosen)} 次测量后，新增 {len(new_pairs)} 项可辨差异（{new_labels}），目标差异合计可辨 {obj_after}/{obj_tot}。"
    elif obj_cur<obj_tot:
        interpretation=f"当前数据可辨测量员差异 {op_cur}/{op_tot}、仪器差异 {in_cur}/{in_tot}。限额内没有能改善可辨性的补测组合，补测单为空；请登记新的可补测组合或提高限额。"
    else:
        interpretation=f"当前数据已可辨全部目标两两差异（测量员 {op_cur}/{op_tot}、仪器 {in_cur}/{in_tot}），无需补测。"
    if unquota: interpretation+=f"另有 {unquota} 组候选未登记对应限额，按0处理未予安排。"
    caveat='可辨性由三项加性模型（纸样＋测量员＋仪器，无交互）的设计秩精确判定；当前估计为最小二乘值，标准误依赖方差齐性与近似正态。补测单基于排队时冻结的读数、候选与限额，源数据更新后自动失效。'
    return {'metrics':metrics,'interpretation':interpretation,'caveat':caveat,
            'pairs':{'columns':['效应','两两对比','当前可辨','当前估计 ΔE','标准误','补测后可辨'],'rows':[pair_row(e) for e in entries]},
            'plan':{'columns':['序号','纸样','测量员','仪器'],'rows':plan_rows},
            'quotas':{'columns':['测量员','仪器','已安排','限额'],'rows':quota_rows},
            'readings':{'columns':['源记录','纸样','测量员','仪器','复测色差 ΔE'],
                        'rows':[[r['source_key'],str(r['values']['paper']),str(r['values']['operator']),str(r['values']['instrument']),float(r['values']['delta_e'])] for r in readings]},
            'table_title':'冻结复测读数明细'}

def _contains1(v,u):
    """单向量张成判定：u 是否为 v 的倍数。"""
    b=_Basis();b.add(v)
    return b.contains(u)
