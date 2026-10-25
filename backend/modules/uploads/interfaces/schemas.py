from typing import Literal,Any
from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator
from foundation.http.schemas import Body

class Upload(Body):
    name:str=Field(min_length=1,max_length=200)
    size:int=Field(gt=0,le=16_000_000)
    content_type:Literal['application/json','text/csv','text/plain']
    purpose:Literal['processing','storage']='processing'
    retention_hours:int=Field(default=24,ge=1,le=720)
    sha256:str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')

