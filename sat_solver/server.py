import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sat_solver.config import config, BASE_DIR, UPLOAD_DIR, OUTPUT_DIR
from sat_solver.prompts import (
    DEFAULT_VISION_SYSTEM_PROMPT,
    DEFAULT_SOLVER_SYSTEM_PROMPT,
)
from sat_solver.engine import (
    JOBS,
    JobStatus,
    QuestionItem,
    process_batch_job,
)

app = FastAPI(title="SAT & Exam AI Solver Platform", version="1.0.0")

# CORS middleware for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static and uploaded files
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


class ConfigUpdateRequest(BaseModel):
    ai_provider: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    vision_model: Optional[str] = None
    solver_model: Optional[str] = None
    max_concurrency: Optional[int] = None


@app.get("/")
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "SAT Solver Platform API is active"})


@app.get("/api/config")
async def get_config():
    return {
        "ai_provider": config.ai_provider,
        "vision_model": config.vision_model,
        "solver_model": config.solver_model,
        "max_concurrency": config.max_concurrency,
        "has_openrouter_key": bool(config.openrouter_api_key.strip()),
        "has_anthropic_key": bool(config.anthropic_api_key.strip()),
    }


@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    update_data = req.model_dump(exclude_unset=True)
    config.update(**update_data)
    return {
        "status": "success",
        "message": "Configuration updated successfully",
        "config": await get_config(),
    }


@app.get("/api/prompts")
async def get_prompts():
    return {
        "vision_system_prompt": DEFAULT_VISION_SYSTEM_PROMPT,
        "solver_system_prompt": DEFAULT_SOLVER_SYSTEM_PROMPT,
    }


@app.post("/api/upload")
async def upload_batch(
    files: List[UploadFile] = File(...),
    vision_prompt: Optional[str] = Form(None),
    solver_prompt: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Receives 1 to 50 screenshots, sets up the job, and starts processing."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    job_id = str(uuid.uuid4())[:8]
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Sort files naturally by filename if possible
    sorted_files = sorted(files, key=lambda f: f.filename or "")

    question_items: List[QuestionItem] = []
    for idx, uploaded_file in enumerate(sorted_files, start=1):
        filename = uploaded_file.filename or f"screenshot_{idx}.png"
        file_path = job_dir / filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(uploaded_file.file, buffer)

        # Web accessible path
        rel_path = f"/uploads/{job_id}/{filename}"
        question_items.append(
            QuestionItem(
                index=idx,
                filename=filename,
                image_path=str(file_path),
                status="pending",
            )
        )

    job_status = JobStatus(
        job_id=job_id,
        status="queued",
        total_images=len(question_items),
        current_message=f"Queued {len(question_items)} screenshots for processing",
        items=question_items,
    )
    JOBS[job_id] = job_status

    # Launch background async batch pipeline
    background_tasks.add_task(
        process_batch_job,
        job_id=job_id,
        vision_prompt=vision_prompt,
        solver_prompt=solver_prompt,
    )

    return {
        "job_id": job_id,
        "total_files": len(question_items),
        "status": "queued",
    }


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Format image paths for frontend viewing
    items_for_frontend = []
    for item in job.items:
        items_for_frontend.append(
            {
                "index": item.index,
                "filename": item.filename,
                "image_url": f"/uploads/{job_id}/{Path(item.image_path).name}",
                "status": item.status,
                "markdown_question": item.markdown_question,
                "solution": item.solution,
                "error": item.error,
            }
        )

    return {
        "job_id": job.job_id,
        "status": job.status,
        "total_images": job.total_images,
        "vision_completed": job.vision_completed,
        "solver_completed": job.solver_completed,
        "current_message": job.current_message,
        "has_questions_md": bool(job.questions_md_path),
        "has_solutions_md": bool(job.solutions_md_path),
        "items": items_for_frontend,
    }


@app.get("/api/export/{job_id}/{file_type}")
async def export_file(job_id: str, file_type: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if file_type == "questions":
        target = OUTPUT_DIR / job_id / "questions.md"
        filename = f"questions_{job_id}.md"
    elif file_type == "solutions":
        target = OUTPUT_DIR / job_id / "solutions.md"
        filename = f"solutions_{job_id}.md"
    else:
        raise HTTPException(
            status_code=400, detail="Invalid file type. Use questions or solutions"
        )

    if not target.exists():
        raise HTTPException(
            status_code=404, detail=f"File {file_type}.md not generated yet"
        )

    return FileResponse(
        str(target),
        media_type="text/markdown",
        filename=filename,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "sat_solver.server:app", host=config.host, port=config.port, reload=True
    )
