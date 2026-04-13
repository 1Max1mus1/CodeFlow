from pydantic import BaseModel
from typing import Optional


class Task(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: int = 1
    owner_email: str


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 1
    owner_email: str


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None


class User(BaseModel):
    id: int
    name: str
    email: str
    is_premium: bool = False


class NotificationPayload(BaseModel):
    recipient_email: str
    subject: str
    body: str
