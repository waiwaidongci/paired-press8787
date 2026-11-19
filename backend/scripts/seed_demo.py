import json
from sqlalchemy import select,func
from src.config.database import Base,engine,Session
from src.config.domain import DOMAIN
from src.models.user import User
from src.models.study import Study
from src.models.observation import Observation
from src.models.candidate import Candidate
from src.models.quota import Quota
from src.models import run,review,audit
from src.utils.security import hash_password

def R(p,o,i,v): return {'paper':p,'operator':o,'instrument':i,'delta_e':v}
def Q(o,i,n): return {'operator':o,'instrument':i,'max_count':n}

# 三项研究的合成业务数据：读数 / 可补测组合 / 每人每台仪器限额
DEMO={
 '栖木·换班归因·米白纸':{
   'readings':[R('米白P1','甲','色差仪A',2.08),R('米白P1','乙','色差仪A',2.31),R('米白P2','乙','色差仪A',2.44),
               R('米白P2','乙','色差仪B',2.57),R('米白P3','丙','色差仪B',2.86),R('米白P4','丙','色差仪B',2.91),
               R('米白P5','甲','色差仪B',2.22),R('米白P5','甲','色差仪B',2.18)],
   'candidates':[R('米白P3','乙','色差仪B',None),R('米白P1','丙','色差仪A',None),R('米白P4','乙','色差仪B',None),
                 R('米白P5','乙','色差仪A',None),R('米白P2','丙','色差仪A',None),R('米白P3','甲','色差仪B',None)],
   'quotas':[Q('乙','色差仪B',1),Q('丙','色差仪A',1),Q('丙','色差仪B',0),Q('甲','色差仪B',1),Q('乙','色差仪A',1)]},
 '栖木·缺格核对·棉纸':{
   'readings':[R('棉P1','小周','色差仪A',1.82),R('棉P1','小周','色差仪A',1.86),
               R('棉P1','小吴','色差仪B',2.31),R('棉P1','小吴','色差仪B',2.27)],
   'candidates':[R('棉P2','小周','色差仪B',None),R('棉P2','小吴','色差仪A',None)],
   'quotas':[Q('小周','色差仪B',1),Q('小吴','色差仪A',1)]},
 '栖木·连通设计·轻涂纸':{
   'readings':[R('轻涂P1','小赵','色差仪A',1.95),R('轻涂P1','小钱','色差仪B',2.12),
               R('轻涂P2','小赵','色差仪B',2.04),R('轻涂P2','小钱','色差仪A',1.88),
               R('轻涂P3','小赵','色差仪A',1.99),R('轻涂P3','小钱','色差仪B',2.16)],
   'candidates':[R('轻涂P4','小赵','色差仪A',None),R('轻涂P4','小钱','色差仪B',None)],
   'quotas':[Q('小赵','色差仪A',1),Q('小钱','色差仪B',1)]},
}

def seed():
    Base.metadata.create_all(engine)
    with Session() as db:
        for role in ('admin','analyst','viewer'):
            email=role+'@demo.local'
            if not db.scalar(select(User).where(User.email==email)): db.add(User(email=email,role=role,password_hash=hash_password('Research2026!')))
        for k,name in enumerate(DOMAIN['names']):
            study=db.scalar(select(Study).where(Study.name==name))
            if not study:
                study=Study(name=name,source_filename=DOMAIN['slug']+f'-202611-{k+1}.csv',description='独立合成业务观测 / 同一工艺换班试印 / 仅用于方法与流程演示');db.add(study);db.flush()
            data=DEMO[name]
            for n,values in enumerate(data['readings']):
                key=f'DEMO-{k+1}-{n+1:04}'
                if not db.scalar(select(Observation.id).where(Observation.study_id==study.id,Observation.source_key==key)):
                    db.add(Observation(study_id=study.id,source_key=key,values=values))
            for combo in data['candidates']:
                if not db.scalar(select(Candidate.id).where(Candidate.study_id==study.id,Candidate.paper==combo['paper'],Candidate.operator==combo['operator'],Candidate.instrument==combo['instrument'])):
                    db.add(Candidate(study_id=study.id,paper=combo['paper'],operator=combo['operator'],instrument=combo['instrument']))
            for q in data['quotas']:
                if not db.scalar(select(Quota.id).where(Quota.study_id==study.id,Quota.operator==q['operator'],Quota.instrument==q['instrument'])):
                    db.add(Quota(study_id=study.id,operator=q['operator'],instrument=q['instrument'],max_count=q['max_count']))
        db.commit()
        counts={model.__tablename__:db.scalar(select(func.count()).select_from(model)) for model in (User,Study,Observation,Candidate,Quota)}
        print(json.dumps(counts,ensure_ascii=False));return counts
if __name__=='__main__': seed()
