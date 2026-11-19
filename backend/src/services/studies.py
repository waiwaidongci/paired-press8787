from fastapi import HTTPException
from sqlalchemy import select,func
from src.models.study import Study
from src.models.observation import Observation
from src.models.candidate import Candidate
from src.models.quota import Quota
from src.services.domain_validation import validate_values,validate_combo,validate_quota
from src.services.audits import log
from src.utils.serializers import record

def _lock(db,id):
    """锁定研究行：改录与排队在同一事务内串行，保证冻结一致。"""
    s=db.scalar(select(Study).where(Study.id==id).with_for_update())
    if not s: raise HTTPException(404,'业务批次不存在')
    return s

def list_studies(db):
    data=[]
    for s in db.scalars(select(Study).order_by(Study.id)):
        x=record(s)
        x['row_count']=db.scalar(select(func.count()).select_from(Observation).where(Observation.study_id==s.id))
        x['candidate_count']=db.scalar(select(func.count()).select_from(Candidate).where(Candidate.study_id==s.id))
        x['quota_count']=db.scalar(select(func.count()).select_from(Quota).where(Quota.study_id==s.id))
        data.append(x)
    return data

def create(db,data,user):
    if db.scalar(select(Study).where(Study.name==data.name)): raise HTTPException(409,'批次名称已存在')
    s=Study(**data.model_dump());db.add(s);log(db,user,'study.create',data.name);db.commit();return record(s)

def require(db,id):
    s=db.get(Study,id)
    if not s: raise HTTPException(404,'业务批次不存在')
    return s

def observations(db,id):
    require(db,id);return [record(x) for x in db.scalars(select(Observation).where(Observation.study_id==id).order_by(Observation.id))]

def candidates(db,id):
    require(db,id);return [record(x) for x in db.scalars(select(Candidate).where(Candidate.study_id==id).order_by(Candidate.id))]

def quotas(db,id):
    require(db,id);return [record(x) for x in db.scalars(select(Quota).where(Quota.study_id==id).order_by(Quota.id))]

def save_observation(db,id,data,user,row_id=None):
    study=_lock(db,id)
    try: values=validate_values(data.values)
    except (ValueError,TypeError) as e: raise HTTPException(422,str(e))
    other=db.scalar(select(Observation).where(Observation.study_id==id,Observation.source_key==data.source_key))
    if other and other.id!=row_id: raise HTTPException(409,'源记录编号重复')
    if row_id:
        row=db.get(Observation,row_id)
        if not row or row.study_id!=id: raise HTTPException(404,'记录不存在')
        row.source_key=data.source_key;row.values=values
    else:
        if db.scalar(select(func.count()).select_from(Observation).where(Observation.study_id==id))>=5000: raise HTTPException(422,'小型研究最多5000行')
        row=Observation(study_id=id,source_key=data.source_key,values=values);db.add(row)
    study.data_version+=1
    log(db,user,'observation.save',f'{id}/{data.source_key} → v{study.data_version}');db.commit();return record(row)

def delete_observation(db,id,row_id,user):
    study=_lock(db,id)
    row=db.get(Observation,row_id)
    if not row or row.study_id!=id: raise HTTPException(404,'记录不存在')
    db.delete(row);study.data_version+=1
    log(db,user,'observation.delete',f'{id}/{row_id} → v{study.data_version}');db.commit();return {'deleted':True}

def save_candidate(db,id,data,user):
    study=_lock(db,id)
    try: combo=validate_combo(data.model_dump())
    except (ValueError,TypeError) as e: raise HTTPException(422,str(e))
    if db.scalar(select(Candidate).where(Candidate.study_id==id,Candidate.paper==combo['paper'],Candidate.operator==combo['operator'],Candidate.instrument==combo['instrument'])):
        raise HTTPException(409,'该可补测组合已登记')
    row=Candidate(study_id=id,**combo);db.add(row)
    study.data_version+=1
    log(db,user,'candidate.save',f"{id}/{combo['paper']}×{combo['operator']}×{combo['instrument']} → v{study.data_version}");db.commit();return record(row)

def delete_candidate(db,id,cid,user):
    study=_lock(db,id)
    row=db.get(Candidate,cid)
    if not row or row.study_id!=id: raise HTTPException(404,'组合不存在')
    db.delete(row);study.data_version+=1
    log(db,user,'candidate.delete',f'{id}/{cid} → v{study.data_version}');db.commit();return {'deleted':True}

def save_quota(db,id,data,user):
    study=_lock(db,id)
    try: q=validate_quota(data.model_dump())
    except (ValueError,TypeError) as e: raise HTTPException(422,str(e))
    row=db.scalar(select(Quota).where(Quota.study_id==id,Quota.operator==q['operator'],Quota.instrument==q['instrument']))
    if row: row.max_count=q['max_count']
    else:
        row=Quota(study_id=id,**q);db.add(row)
    study.data_version+=1
    log(db,user,'quota.save',f"{id}/{q['operator']}×{q['instrument']}≤{q['max_count']} → v{study.data_version}");db.commit();return record(row)

def delete_quota(db,id,qid,user):
    study=_lock(db,id)
    row=db.get(Quota,qid)
    if not row or row.study_id!=id: raise HTTPException(404,'限额不存在')
    db.delete(row);study.data_version+=1
    log(db,user,'quota.delete',f'{id}/{qid} → v{study.data_version}');db.commit();return {'deleted':True}
