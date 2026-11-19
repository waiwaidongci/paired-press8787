"""端到端核对：登记→冻结排队→计算→失效。

覆盖：排队时一起冻结读数/候选/限额与数据版本；并发改录后旧单立即失效；
计算晚到不能重新发出旧单（stale）；候选超过24组拒绝排队；失效单不能复核与导出。
"""
import pytest
from tests.conftest import login
from src.config.database import Session
from src.services.execute import execute

def R(p,o,i,v): return {'paper':p,'operator':o,'instrument':i,'delta_e':v}

def make_study(client,h,name='换班归因·测试'):
    r=client.post('/studies',json={'name':name,'source_filename':'t-202611.csv','description':'测试'},headers=h)
    assert r.status_code==200,r.text
    return r.json()['id']

def add_reading(client,h,sid,key,p,o,i,v):
    r=client.post(f'/studies/{sid}/observations',json={'source_key':key,'values':R(p,o,i,v)},headers=h)
    assert r.status_code==200,r.text

def add_candidate(client,h,sid,p,o,i):
    r=client.post(f'/studies/{sid}/candidates',json={'paper':p,'operator':o,'instrument':i},headers=h)
    assert r.status_code==200,r.text

def add_quota(client,h,sid,o,i,n):
    r=client.post(f'/studies/{sid}/quotas',json={'operator':o,'instrument':i,'max_count':n},headers=h)
    assert r.status_code==200,r.text

def seed_gap(client,h,sid):
    add_reading(client,h,sid,'R1','棉P1','小周','仪A',1.82)
    add_reading(client,h,sid,'R2','棉P1','小周','仪A',1.86)
    add_reading(client,h,sid,'R3','棉P1','小吴','仪B',2.31)
    add_reading(client,h,sid,'R4','棉P1','小吴','仪B',2.27)
    add_candidate(client,h,sid,'棉P2','小周','仪B')
    add_candidate(client,h,sid,'棉P2','小吴','仪A')
    add_quota(client,h,sid,'小周','仪B',1)
    add_quota(client,h,sid,'小吴','仪A',1)

def queue_run(client,h,sid,name='核算'):
    r=client.post('/runs',json={'study_id':sid,'name':name,'parameters':{}},headers=h)
    assert r.status_code==200,r.text
    return r.json()

def test_freeze_queue_execute_flow(client,tmp_path):
    h=login(client,'analyst@demo.local')
    sid=make_study(client,h)
    seed_gap(client,h,sid)
    run=queue_run(client,h,sid)
    # 排队时一起冻结读数、候选组合与限额
    assert run['status']=='queued' and run['data_version']>0
    snap=run['snapshot']
    assert len(snap['readings'])==4 and len(snap['candidates'])==2 and len(snap['quotas'])==2
    with Session() as db: execute(db,run['id'],artifacts=str(tmp_path))
    r=client.get(f"/runs/{run['id']}",headers=h).json()
    assert r['status']=='completed' and r['valid'] is True
    assert r['result']['metrics']['补测后新增可辨差异']==2
    assert len(r['result']['plan']['rows'])==2
    assert (tmp_path/f"run-{run['id']}.json").exists()

def test_edit_invalidates_old_plan_immediately(client,tmp_path):
    h=login(client,'analyst@demo.local')
    sid=make_study(client,h)
    seed_gap(client,h,sid)
    run=queue_run(client,h,sid)
    with Session() as db: execute(db,run['id'],artifacts=str(tmp_path))
    assert client.get(f"/runs/{run['id']}",headers=h).json()['valid'] is True
    # 源数据更新 → 旧单立即失效
    add_reading(client,h,sid,'R5','棉P2','小周','仪B',1.91)
    r=client.get(f"/runs/{run['id']}",headers=h).json()
    assert r['valid'] is False and r['current_data_version']>r['data_version']
    # 失效单不能复核、不能导出
    admin=login(client,'admin@demo.local')
    assert client.post(f"/runs/{run['id']}/review",json={'note':'复核意见：同意'},headers=admin).status_code==409
    assert client.get(f"/runs/{run['id']}/export",headers=admin).status_code==409

def test_late_computation_cannot_reissue_old_plan(client,tmp_path):
    h=login(client,'analyst@demo.local')
    sid=make_study(client,h)
    seed_gap(client,h,sid)
    run=queue_run(client,h,sid)
    # 排队后、计算完成前改录 → 晚到的计算只能作废，不能发出旧单
    add_quota(client,h,sid,'小周','仪B',2)
    with Session() as db: execute(db,run['id'],artifacts=str(tmp_path))
    r=client.get(f"/runs/{run['id']}",headers=h).json()
    assert r['status']=='stale' and r['valid'] is False
    assert not (tmp_path/f"run-{run['id']}.json").exists()
    # 再次执行也不会复活旧单
    with Session() as db: execute(db,run['id'],artifacts=str(tmp_path))
    assert client.get(f"/runs/{run['id']}",headers=h).json()['status']=='stale'

def test_candidate_capacity_over_24_refused(client):
    h=login(client,'analyst@demo.local')
    sid=make_study(client,h)
    add_reading(client,h,sid,'R1','P1','甲','A',2.0)
    for i in range(25): add_candidate(client,h,sid,f'P{i+2}','甲','A')
    r=client.post('/runs',json={'study_id':sid,'name':'超限','parameters':{}},headers=h)
    assert r.status_code==422 and '24' in r.json()['detail']

def test_freeze_is_atomic_under_edits(client):
    # 冻结快照必须同时包含读数、候选与限额；之后的改录不影响快照
    h=login(client,'analyst@demo.local')
    sid=make_study(client,h)
    seed_gap(client,h,sid)
    run=queue_run(client,h,sid)
    add_candidate(client,h,sid,'棉P3','小周','仪A')
    r=client.get(f"/runs/{run['id']}",headers=h).json()
    assert len(r['snapshot']['candidates'])==2 and len(r['snapshot']['quotas'])==2
    assert r['valid'] is False  # 排队后改录使旧单立即失效（queued 状态同样失效）

def test_quota_and_candidate_validation(client):
    h=login(client,'analyst@demo.local')
    sid=make_study(client,h)
    add_reading(client,h,sid,'R1','P1','甲','A',2.0)
    assert client.post(f'/studies/{sid}/quotas',json={'operator':'甲','instrument':'A','max_count':25},headers=h).status_code==422
    assert client.post(f'/studies/{sid}/candidates',json={'paper':'','operator':'甲','instrument':'A'},headers=h).status_code==422
    dup=client.post(f'/studies/{sid}/candidates',json={'paper':'P9','operator':'甲','instrument':'A'},headers=h)
    assert dup.status_code==200
    assert client.post(f'/studies/{sid}/candidates',json={'paper':'P9','operator':'甲','instrument':'A'},headers=h).status_code==409

def test_viewer_readonly_and_export_rules(client,tmp_path):
    h=login(client,'analyst@demo.local')
    sid=make_study(client,h)
    seed_gap(client,h,sid)
    run=queue_run(client,h,sid)
    with Session() as db: execute(db,run['id'],artifacts=str(tmp_path))
    viewer=login(client,'viewer@demo.local')
    assert client.post(f'/studies/{sid}/observations',json={'source_key':'X','values':R('P','甲','A',1.0)},headers=viewer).status_code==403
    # 观察员只能导出已复核结果
    assert client.get(f"/runs/{run['id']}/export",headers=viewer).status_code==403
    admin=login(client,'admin@demo.local')
    assert client.post(f"/runs/{run['id']}/review",json={'note':'同意补测安排'},headers=admin).status_code==200
    assert client.get(f"/runs/{run['id']}/export",headers=viewer).status_code==200
