from pydantic import BaseModel,Field
class QuotaInput(BaseModel):
    operator:str=Field(min_length=1,max_length=40)
    instrument:str=Field(min_length=1,max_length=40)
    max_count:int=Field(ge=0,le=24)
