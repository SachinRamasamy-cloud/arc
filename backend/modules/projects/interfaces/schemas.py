from typing import Literal,Any
from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator
from foundation.http.schemas import Body
from modules.tenancy.interfaces.schemas import Name

class CreateProject(Name): description:str=Field(default='',max_length=500)

