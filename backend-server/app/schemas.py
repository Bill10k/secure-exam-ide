from pydantic import BaseModel
from typing import Optional

class LaunchRequest(BaseModel):
    jwt: str

class ExamSessionResponse(BaseModel):
    id: int
    context_id: str
    resource_link_id: str
    user_id: str
    status: str

    class Config:
        from_attributes = True

class LaunchResponse(BaseModel):
    message: str
    session: ExamSessionResponse
