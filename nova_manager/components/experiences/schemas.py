from uuid import UUID as UUIDType
from pydantic import BaseModel


class ExperienceResponse(BaseModel):
    pid: UUIDType
    name: str
    description: str
    status: str

    class Config:
        from_attributes = True
