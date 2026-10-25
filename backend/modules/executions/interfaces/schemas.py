from typing import Literal,Any
from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator
from foundation.http.schemas import Body

class Run(Body):
    operation:Literal['validate','normalize','csv_to_json','json_to_csv','workflow']='validate'
    data:Any=None
    file_id:str|None=None
    required_fields:list[str]=Field(default_factory=list,max_length=64)
    mappings:dict[str,str]=Field(default_factory=dict)
    lowercase:list[str]=Field(default_factory=list,max_length=64)
    max_credits_milli:int=Field(default=10_000,ge=0,le=1_000_000)
    workflow_id:str|None=None
    version:int|None=Field(default=None,ge=1)
    @field_validator('mappings')
    @classmethod
    def cap_mapping(cls,v):
        if len(v)>64: raise ValueError('too many fields')
        return v

