from pydantic import BaseModel
from typing import List, Optional

class TaskItem(BaseModel):
    id: Optional[int] = None
    title: str
    deadline: str
    priority: str
    action_required: str
    status: Optional[str] = "Pending"
    category: Optional[str] = "Actionable"

class TaskUpdateStatus(BaseModel):
    status: str

class TaskExtractionResult(BaseModel):
    document_id: Optional[int] = None
    document_summary: str
    tasks: List[TaskItem]
    future_action_items: List[TaskItem] = []