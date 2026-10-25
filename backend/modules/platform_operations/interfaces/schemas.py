from typing import Literal,Any
from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator
from foundation.http.schemas import Body

class OperatorAction(Body):
    status:Literal['active','suspended']
    reason:str=Field(min_length=10,max_length=240)

