from typing import Literal,Any
from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator


class Body(BaseModel):
    model_config=ConfigDict(extra='forbid')
