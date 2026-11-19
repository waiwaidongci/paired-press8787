from pydantic import BaseModel,Field
class CandidateComboInput(BaseModel):
    paper:str=Field(min_length=1,max_length=40)
    operator:str=Field(min_length=1,max_length=40)
    instrument:str=Field(min_length=1,max_length=40)
CandidateInput=CandidateComboInput
