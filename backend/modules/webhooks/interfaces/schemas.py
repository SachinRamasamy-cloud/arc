from typing import Literal,Any
from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator
from foundation.http.schemas import Body

class Hook(Body): url:str=Field(min_length=10,max_length=2000)

