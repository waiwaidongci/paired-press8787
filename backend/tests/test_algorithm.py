"""算法核对：可估性判定与限额内补测规划。

独立 oracle：缺格设计单项补测无效、成对补测可辨；连通设计全部可辨；
同数时少测；限额阻断；空候选空单；非法输入拒绝。
"""
import pytest
from src.services.algorithm import calculate

def mk(p,o,i,v=1.0,k='T'):
    return {'source_key':f'{k}-{p}-{o}-{i}','values':{'paper':p,'operator':o,'instrument':i,'delta_e':v}}

def snap(readings,candidates=(),quotas=()):
    return {'readings':readings,
            'candidates':[{'paper':p,'operator':o,'instrument':i} for p,o,i in candidates],
            'quotas':[{'operator':o,'instrument':i,'max_count':n} for o,i,n in quotas]}

# 缺格数据：读数 (P1,甲,A) 与 (P1,乙,B)，候选两格 (P2,甲,B) (P2,乙,A)
GAP_READS=[mk('P1','甲','A',2.0),mk('P1','甲','A',2.1),mk('P1','乙','B',2.6),mk('P1','乙','B',2.5)]
GAP_CANDS=[('P2','甲','B'),('P2','乙','A')]
GAP_QUOTAS=[('甲','B',1),('乙','A',1)]

def test_missing_cell_single_ineffective_together_works():
    # 单项补测不可辨
    for keep in (0,1):
        r=calculate(snap(GAP_READS,[GAP_CANDS[keep]],GAP_QUOTAS),{})
        assert r['metrics']['补测后新增可辨差异']==0
        assert r['plan']['rows']==[]
    # 两格合起来可辨 测量员甲−乙 与 仪器A−B
    r=calculate(snap(GAP_READS,GAP_CANDS,GAP_QUOTAS),{})
    assert r['metrics']['测量员两两差异·当前可辨']=='0 / 1'
    assert r['metrics']['仪器两两差异·当前可辨']=='0 / 1'
    assert len(r['plan']['rows'])==2
    assert r['metrics']['补测后新增可辨差异']==2
    after={(row[0],row[1]):row[5] for row in r['pairs']['rows']}
    assert all(v=='是' for k,v in after.items() if k[0] in ('测量员','仪器'))

def test_connected_design_needs_no_supplement():
    reads=[mk('P1','甲','A',2.0),mk('P1','乙','B',2.4),mk('P2','甲','B',2.1),mk('P2','乙','A',2.5),mk('P3','甲','A',1.9),mk('P3','乙','B',2.6)]
    r=calculate(snap(reads,[('P4','甲','A')],[('甲','A',1)]),{})
    assert r['metrics']['补测后目标差异可辨']=='2 / 2'
    assert r['plan']['rows']==[] and r['metrics']['补测后新增可辨差异']==0

def test_quota_zero_blocks_candidate():
    r=calculate(snap(GAP_READS,GAP_CANDS,[('甲','B',0),('乙','A',0)]),{})
    assert r['plan']['rows']==[]
    assert '限额内没有能改善可辨性的补测组合' in r['interpretation']

def test_fewer_measurements_wins_tie():
    # 候选 (P1,甲,B) 单独可辨两对；候选 (P2,甲,B)+(P2,乙,A) 合起来也可辨两对 → 选少测
    cands=[('P2','甲','B'),('P2','乙','A'),('P1','甲','B')]
    quotas=[('甲','B',2),('乙','A',1)]
    r=calculate(snap(GAP_READS[:2]+GAP_READS[2:],cands,quotas),{})
    assert r['metrics']['补测后新增可辨差异']==2
    assert len(r['plan']['rows'])==1
    assert r['plan']['rows'][0][1:]==['P1','甲','B']

def test_each_combo_at_most_once():
    # 同一组合至多安排一次：单格增益为0时不重复占用
    r=calculate(snap(GAP_READS,GAP_CANDS,[('甲','B',24),('乙','A',24)]),{})
    keys=[tuple(row[1:]) for row in r['plan']['rows']]
    assert len(keys)==len(set(keys))

def test_empty_candidates_empty_plan():
    r=calculate(snap(GAP_READS,[],[]),{})
    assert r['plan']['rows']==[]
    assert r['metrics']['候选组合数']==0

def test_estimates_match_hand_calculation():
    reads=[mk('P1','甲','A',2.0),mk('P1','乙','A',2.7),mk('P2','甲','A',3.0),mk('P2','乙','A',3.7)]
    r=calculate(snap(reads),{})
    row=[x for x in r['pairs']['rows'] if x[0]=='测量员'][0]
    assert row[2]=='是' and abs(row[3]-0.7)<1e-9

def test_invalid_inputs_rejected():
    with pytest.raises(ValueError): calculate({'readings':[]},{})
    bad=mk('P1','甲','A',float('nan'))
    with pytest.raises(ValueError): calculate(snap([bad]),{})
    missing={'source_key':'x','values':{'paper':'P1','operator':'甲','instrument':'A'}}
    with pytest.raises(ValueError): calculate({'readings':[missing]},{})

def test_plan_is_deterministic():
    a=calculate(snap(GAP_READS,GAP_CANDS,GAP_QUOTAS),{})
    b=calculate(snap(GAP_READS,GAP_CANDS,GAP_QUOTAS),{})
    assert a['plan']['rows']==b['plan']['rows']
