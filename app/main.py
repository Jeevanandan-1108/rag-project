
print("THIS MAIN FILE IS RUNNING")

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uuid
from dotenv import load_dotenv
import os
from app.blob_storage import upload_pdf_to_blob

load_dotenv()

from app.ingestion import ingest_uploaded_pdf
from app.rag import chat


app = FastAPI()

# -----------------------------------------
# Paths
# -----------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# -----------------------------------------
# Request Schema
# -----------------------------------------
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    document_id :Optional[str]=None


# -----------------------------------------
# Serve Frontend
# -----------------------------------------
@app.get("/", response_class=HTMLResponse)
def serve_ui():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# -----------------------------------------
# Chat Endpoint
# -----------------------------------------
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):

    print("CHAT ENDPOINT HIT")

    try:
        session_id = request.session_id or str(uuid.uuid4())

        answer_data = await chat(
            message=request.message,
            session_id=session_id,
            document_id=request.document_id
        )

        print("ANSWER DATA:", answer_data)

        return {
            "answer": answer_data.get("answer"),
            "sources": answer_data.get("sources", []),
            "retrieval_debug": answer_data.get("retrieval_debug", []),
            "session_id": session_id
        }

    except Exception as e:
        print("ERROR OCCURRED:", str(e))
        raise e


# -----------------------------------------
# Upload Endpoint
# -----------------------------------------
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):

    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files allowed."}

    content = await file.read()

    document_id = str(uuid.uuid4())

    # Upload to Blob Storage
    blob_filename = f"{document_id}_{file.filename}"
    blob_url = upload_pdf_to_blob(content, blob_filename)

    result = await ingest_uploaded_pdf(
        content=content,
        file_name=file.filename,
        document_id=document_id,
        blob_url=blob_url
    )

    return {
        "message": "PDF uploaded successfully",
        "document_id": document_id,
        "blob_url": blob_url,
        "details": result
    }