import json,logging
from pathlib import Path
from sqlalchemy import select
from src.models.run import Run
from src.models.study import Study
from src.services.algorithm import calculate
from src.utils.serializers import checksum

def execute(db,run_id,artifacts='/app/artifacts'):
    """执行一次排队任务。完成前复核数据版本：源数据已更新则标记失效，
    晚到的计算不能重新发出旧补测单。"""
    run=db.get(Run,run_id)
    if not run or run.status not in ('queued','running'): return
    run.status='running';db.commit()
    try:
        if checksum(run.snapshot)!=run.checksum: raise ValueError('输入快照校验失败')
        result=calculate(run.snapshot,run.parameters or {})
        result['input_sha256']=run.checksum
        result['data_version']=run.data_version
        study=db.scalar(select(Study).where(Study.id==run.study_id).with_for_update())
        run.result=result
        if study is None or study.data_version!=run.data_version:
            run.status='stale'
            run.error=f'计算期间源数据已从 v{run.data_version} 更新，补测单作废'
        else:
            run.status='completed'
            Path(artifacts).mkdir(parents=True,exist_ok=True)
            Path(f'{artifacts}/run-{run_id}.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False))
    except Exception as e:
        logging.exception('analysis failed');run.status='failed';run.error=str(e)
    db.commit()
