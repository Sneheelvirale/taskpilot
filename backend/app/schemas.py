from pydantic import BaseModel
from typing import List, Optional

class Task(BaseModel):
    title: str
    deadline: Optional[str] = None
    priority: str  # High, Medium, Low
    action_required: str

class TaskExtractionResult(BaseModel):
    document_summary: str
    tasks: List[Task]