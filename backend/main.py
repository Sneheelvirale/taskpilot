from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.db import init_db, get_db, DocumentRecord, TaskRecord
from app.parser import extract_text_from_file
from app.schemas import TaskExtractionResult, TaskItem, TaskUpdateStatus
from app.ai.extractor import extract_tasks_with_nemotron

init_db()

app = FastAPI(title="TaskPilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "TaskPilot Backend Running with SQLite Persistence"}

@app.post("/api/extract", response_model=TaskExtractionResult)
async def process_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    allowed_exts = (".pdf", ".txt", ".eml")
    if not file.filename.lower().endswith(allowed_exts):
        raise HTTPException(status_code=400, detail="Only PDF, TXT, and EML files are supported.")

    try:
        file_bytes = await file.read()
        text = extract_text_from_file(file_bytes, file.filename)

        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Could not extract text from document.")

        result = extract_tasks_with_nemotron(text)

        # Persist Document to DB
        doc_record = DocumentRecord(filename=file.filename, summary=result.document_summary)
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        # Categorize and Persist Tasks
        actionable_list = []
        future_list = []

        for task_data in result.tasks:
            # Route low priority or long-term tasks to Future Action Items sidebar
            is_future = task_data.priority.lower() == "low" or "future" in task_data.deadline.lower()
            cat = "Future" if is_future else "Actionable"

            t_rec = TaskRecord(
                document_id=doc_record.id,
                title=task_data.title,
                deadline=task_data.deadline,
                priority=task_data.priority,
                action_required=task_data.action_required,
                status="Pending",
                category=cat
            )
            db.add(t_rec)
            db.commit()
            db.refresh(t_rec)

            item = TaskItem(
                id=t_rec.id,
                title=t_rec.title,
                deadline=t_rec.deadline,
                priority=t_rec.priority,
                action_required=t_rec.action_required,
                status=t_rec.status,
                category=t_rec.category
            )

            if cat == "Actionable":
                actionable_list.append(item)
            else:
                future_list.append(item)

        return TaskExtractionResult(
            document_id=doc_record.id,
            document_summary=doc_record.summary,
            tasks=actionable_list,
            future_action_items=future_list
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# CRUD: Update Task Status
@app.patch("/api/tasks/{task_id}/status")
def update_task_status(task_id: int, payload: TaskUpdateStatus, db: Session = Depends(get_db)):
    task = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = payload.status
    db.commit()
    return {"status": "success", "task_id": task_id, "new_status": task.status}

# CRUD: Fetch All Stored Tasks
@app.get("/api/tasks")
def get_all_tasks(db: Session = Depends(get_db)):
    tasks = db.query(TaskRecord).all()
    return tasks

# Export Task to iCal (.ics) Calendar File
@app.get("/api/tasks/{task_id}/export-ics")
def export_task_ics(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    dt_stamp = datetime.utcnow().strftime("%Y%M%DT%H%M%SZ")
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//TaskPilot AI//EN
BEGIN:VEVENT
UID:taskpilot-{task.id}@{dt_stamp}
DTSTAMP:{dt_stamp}
SUMMARY:{task.title}
DESCRIPTION:{task.action_required} (Priority: {task.priority})
END:VEVENT
END:VCALENDAR"""

    return Response(content=ics_content, media_type="text/calendar", headers={"Content-Disposition": f"attachment; filename=task-{task.id}.ics"})