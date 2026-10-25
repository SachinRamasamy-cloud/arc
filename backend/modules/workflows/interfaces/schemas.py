from typing import Literal,Any
from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator
from foundation.http.schemas import Body
from modules.tenancy.interfaces.schemas import Name

class WorkflowBody(Name):
    graph:dict
    revision:int=Field(default=1,ge=1)

