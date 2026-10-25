from typing import Literal,Any
from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator
from foundation.http.schemas import Body

class CreateKey(Body):
    label:str=Field(min_length=1,max_length=80)
    environment:Literal['test','live']='test'
    scopes:list[Literal['jobs:read','jobs:write','files:read','files:write','data:read','data:write']]=Field(min_length=1,max_length=6)
    expires_days:int=Field(default=30,ge=1,le=90)

