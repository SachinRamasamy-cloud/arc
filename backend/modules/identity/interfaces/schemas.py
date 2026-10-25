from typing import Literal,Any
from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator
from foundation.http.schemas import Body

class Signup(Body):
    email:EmailStr
    password:str=Field(min_length=12,max_length=128)
    name:str=Field(min_length=1,max_length=80)
    accept_terms:bool


class Login(Body):
    email:EmailStr
    password:str=Field(max_length=128)
    code:str=Field(default='',max_length=64)


class Email(Body): email:EmailStr


class TokenBody(Body): token:str=Field(min_length=16,max_length=200)


class Reset(TokenBody): password:str=Field(min_length=12,max_length=128)


class Code(Body): code:str=Field(min_length=6,max_length=64)


class Preferences(Body):
    reduced_motion:bool=False
    compact:bool=False
    timezone:str=Field(default='UTC',max_length=80)
    job_email:bool=False
    usage_email:bool=True
