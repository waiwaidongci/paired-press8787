from sqlalchemy import Column,Integer,String,ForeignKey,UniqueConstraint
from src.config.database import Base
class Quota(Base):
    __tablename__='quotas'
    __table_args__=(UniqueConstraint('study_id','operator','instrument'),)
    id=Column(Integer,primary_key=True)
    study_id=Column(Integer,ForeignKey('studies.id'),nullable=False)
    operator=Column(String(40),nullable=False)
    instrument=Column(String(40),nullable=False)
    max_count=Column(Integer,nullable=False,default=0)
