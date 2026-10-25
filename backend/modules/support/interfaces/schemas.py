from typing import Literal,Any
from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator
from foundation.http.schemas import Body

class Ticket(Body):
    email:EmailStr
    subject:str=Field(min_length=4,max_length=160)
    message:str=Field(min_length=10,max_length=4000)


class Reply(Body):
    reply:str=Field(min_length=1,max_length=4000)
    state:Literal['open','answered','closed']='answered'

