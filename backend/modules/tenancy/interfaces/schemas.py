from typing import Literal,Any
from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator
from foundation.http.schemas import Body

class Name(Body): name:str=Field(min_length=1,max_length=80)


class Invite(Body):
    email:EmailStr
    role:Literal['admin','developer','billing','viewer']


class Role(Body): role:Literal['admin','developer','billing','viewer']

