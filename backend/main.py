from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.parser import extract_text_from_file
from app.schemas import TaskExtractionResult
from app.ai.extractor import extract_tasks_with_nemotron

load_dotenv()

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
    return {"status": "TaskPilot Backend Running"}

@app.post("/api/extract", response_model=TaskExtractionResult)
async def process_document(file: UploadFile = File(...)):
    allowed_exts = (".pdf", ".txt", ".eml")
    if not file.filename.lower().endswith(allowed_exts):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF, TXT, and EML files are supported."
        )

    try:
        file_bytes = await file.read()
        text = extract_text_from_file(file_bytes, file.filename)

        if not text or len(text.strip()) == 0:
            raise HTTPException(
                status_code=400, 
                detail="Could not extract text from document."
            )

        result = extract_tasks_with_nemotron(text)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))