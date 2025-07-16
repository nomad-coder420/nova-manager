import uuid
from fastapi_users import schemas
from pydantic import BaseModel, Field



class UserRead(schemas.BaseUser[int]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass
 

class OrganisationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Organization name")

class OrganisationRead(BaseModel):
    pid: str
    name: str

class AppResponse(BaseModel):
    pid: str
    name: str
