from sqlalchemy import Column,Integer,String,ForeignKey,UniqueConstraint
from src.config.database import Base
class CandidateCombo(Base):
    __tablename__='candidates'
    __table_args__=(UniqueConstraint('study_id','paper','operator','instrument'),)
    id=Column(Integer,primary_key=True)
    study_id=Column(Integer,ForeignKey('studies.id'),nullable=False)
    paper=Column(String(40),nullable=False)
    operator=Column(String(40),nullable=False)
    instrument=Column(String(40),nullable=False)
Candidate=CandidateCombo
