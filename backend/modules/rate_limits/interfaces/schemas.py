from typing import Literal,Any
from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator
from foundation.http.schemas import Body

class Limits(Body):
    rpm:int=Field(ge=1,le=600)
    concurrency:int=Field(ge=1,le=10)
    monthly_cap_milli:int=Field(ge=0,le=10_000_000)
    retention_hours:int=Field(ge=1,le=168)

