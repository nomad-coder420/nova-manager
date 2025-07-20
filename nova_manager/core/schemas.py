from uuid import UUID as UUIDType
from pydantic import BaseModel


class PidResponse(BaseModel):
    pid: UUIDType
