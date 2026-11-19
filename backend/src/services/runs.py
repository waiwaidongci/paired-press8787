import os,json,csv,io
from redis import Redis
from sqlalchemy import select
from fastapi import HTTPException
from src.models.run import Run
from src.models.study import Study
from src.models.review import Review
from src.models.observation import Observation
from src.models.candidate import Candidate
from src.models.quota import Quota
from src.services.domain_validation import validate_parameters,MAX_CANDIDATES
from src.services.audits import log
from src.utils.serializers import record,now,checksum

def create(db,data,user):
    # 锁定研究行：与并发改录串行，排队时一起冻结读数、候选组合与限额
    study=db.scalar(select(Study).where(Study.id==data.study_id).with_for_update())
    if not study: raise HTTPException(404,'业务批次不存在')
    rows=db.scalars(select(Observation).where(Observation.study_id==study.id).order_by(Observation.id)).all()
    if not rows: raise HTTPException(422,'先录入至少一条复测读数')
    cands=db.scalars(select(Candidate).where(Candidate.study_id==study.id).order_by(Candidate.id)).all()
    if len(cands)>MAX_CANDIDATES: raise HTTPException(422,f'候选补测组合{len(cands)}组超过上限{MAX_CANDIDATES}组，请精简后再排队')
    quotas=db.scalars(select(Quota).where(Quota.study_id==study.id).order_by(Quota.id)).all()
    try: params=validate_parameters(data.parameters)
    except (ValueError,TypeError) as e: raise HTTPException(422,str(e))
    snapshot={'readings':[{'source_key':x.source_key,'values':x.values} for x in rows],
              'candidates':[{'paper':x.paper,'operator':x.operator,'instrument':x.instrument} for x in cands],
              'quotas':[{'operator':x.operator,'instrument':x.instrument,'max_count':x.max_count} for x in quotas]}
    run=Run(study_id=study.id,name=data.name,parameters=params,snapshot=snapshot,checksum=checksum(snapshot),
            data_version=study.data_version,created_at=now(),status='queued')
    db.add(run);db.flush();log(db,user,'run.queue',f'{run.id} @ v{study.data_version}');db.commit()
    Redis.from_url(os.environ['REDIS_URL']).rpush('analysis-queue',run.id)
    return get(db,run.id)

def _decorate(db,run):
    result=record(run)
    study=db.get(Study,run.study_id)
    result['current_data_version']=study.data_version if study else None
    result['valid']=bool(run.status=='completed' and study and study.data_version==run.data_version)
    return result

def get(db,id):
    run=db.get(Run,id)
    if not run: raise HTTPException(404,'运行不存在')
    result=_decorate(db,run)
    review=db.scalar(select(Review).where(Review.run_id==id));result['review']=record(review) if review else None
    return result

def list_runs(db):
    return [get(db,x) for x in db.scalars(select(Run.id).order_by(Run.id.desc()))]

def approve(db,id,data,user):
    run=db.get(Run,id)
    if not run: raise HTTPException(404,'运行不存在')
    if run.status!='completed': raise HTTPException(409,'只能复核已完成运行')
    if not _decorate(db,run)['valid']: raise HTTPException(409,'源数据已更新，该补测单已失效，请重新排队')
    if db.scalar(select(Review).where(Review.run_id==id)): raise HTTPException(409,'已复核，记录不可覆盖')
    obj=Review(run_id=id,note=data.note,author=user.email,created_at=now());db.add(obj);log(db,user,'review.approve',f'{id}: {data.note}');db.commit();return record(obj)

def export(db,id,user):
    r=get(db,id)
    if r['status']!='completed': raise HTTPException(409,'尚无完成结果')
    if not r['valid']: raise HTTPException(409,'源数据已更新，该补测单已失效，不能导出')
    if user.role=='viewer' and not r['review']: raise HTTPException(403,'观察员只能导出已复核结果')
    res=r['result']
    stream=io.StringIO();w=csv.writer(stream)
    w.writerow(['运行编号','输入校验SHA256','数据版本','类别','项目','值'])
    for k,v in res['metrics'].items(): w.writerow([id,r['checksum'],r['data_version'],'指标',k,json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v])
    for row in res['pairs']['rows']: w.writerow([id,r['checksum'],r['data_version'],'两两差异',f'{row[0]} {row[1]}',f"当前可辨:{row[2]} 估计:{row[3]} 标准误:{row[4]} 补测后可辨:{row[5]}"])
    for row in res['plan']['rows']: w.writerow([id,r['checksum'],r['data_version'],'补测单',f'第{row[0]}项',f'纸样{row[1]} × 测量员{row[2]} × 仪器{row[3]}'])
    for row in res['quotas']['rows']: w.writerow([id,r['checksum'],r['data_version'],'限额占用',f'{row[0]}×{row[1]}',f'{row[2]} / {row[3]}'])
    w.writerow([id,r['checksum'],r['data_version'],'解释','',res['interpretation']])
    log(db,user,'run.export',id);db.commit()
    return '﻿'+stream.getvalue()
