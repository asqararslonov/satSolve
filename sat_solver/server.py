import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sat_solver.config import config, BASE_DIR, UPLOAD_DIR, OUTPUT_DIR
from sat_solver.prompts import (
    DEFAULT_VISION_SYSTEM_PROMPT,
    DEFAULT_SOLVER_SYSTEM_PROMPT,
    DEFAULT_GROUPING_SYSTEM_PROMPT,
)
from sat_solver.engine import (
    JOBS,
    JobStatus,
    QuestionItem,
    process_batch_job,
    call_vision_api,
    call_solver_api,
    call_grouping_agent,
)

app = FastAPI(title="SAT & Exam AI Solver Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    STATIC_DIR = BASE_DIR / "public"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if UPLOAD_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


class ConfigUpdateRequest(BaseModel):
    ai_provider: Optional[str] = None
    omni_route_url: Optional[str] = None
    omni_route_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    vision_model: Optional[str] = None
    solver_model: Optional[str] = None
    max_concurrency: Optional[int] = None


class ProcessItemRequest(BaseModel):
    job_id: str
    item_index: int
    vision_prompt: Optional[str] = None
    solver_prompt: Optional[str] = None


api = APIRouter()


@api.get("/config")
async def get_config():
    return {
        "ai_provider": config.ai_provider,
        "omni_route_url": config.omni_route_url,
        "vision_model": config.vision_model,
        "solver_model": config.solver_model,
        "max_concurrency": config.max_concurrency,
        "has_omni_route_key": bool(config.omni_route_api_key.strip()),
        "has_openrouter_key": bool(config.openrouter_api_key.strip()),
        "has_anthropic_key": bool(config.anthropic_api_key.strip()),
    }


@api.post("/config")
async def update_config(req: ConfigUpdateRequest):
    update_data = req.model_dump(exclude_unset=True)
    config.update(**update_data)
    return {
        "status": "success",
        "message": "Configuration updated successfully",
        "config": await get_config(),
    }


@api.get("/prompts")
async def get_prompts():
    return {
        "grouping_system_prompt": DEFAULT_GROUPING_SYSTEM_PROMPT,
        "vision_system_prompt": DEFAULT_VISION_SYSTEM_PROMPT,
        "solver_system_prompt": DEFAULT_SOLVER_SYSTEM_PROMPT,
    }


class GroupScreenshotsRequest(BaseModel):
    images: List[dict]  # [{"index": int, "filename": str, "b64": str, "mime_type": str}]
    grouping_prompt: Optional[str] = None


@api.post("/group-screenshots")
async def group_screenshots(req: GroupScreenshotsRequest):
    """AI Agent that analyzes all screenshots together to group them into cohesive questions with correct numbering."""
    try:
        grouping = await call_grouping_agent(req.images, req.grouping_prompt)
        return {"status": "success", "grouping": grouping}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DirectTranscribeRequest(BaseModel):
    image_base64: Optional[str] = None
    image_mime_type: Optional[str] = "image/png"
    images: Optional[List[dict]] = None  # [{"b64": str, "mime_type": str}]
    question_num: int = 1
    vision_prompt: Optional[str] = None


class DirectSolveRequest(BaseModel):
    markdown_question: str
    question_num: int = 1
    solver_prompt: Optional[str] = None


@api.post("/transcribe-direct")
async def transcribe_direct(req: DirectTranscribeRequest):
    """Stateless transcribe of one or more screenshots belonging to a question."""
    try:
        md = await call_vision_api(
            question_num=req.question_num,
            custom_prompt=req.vision_prompt,
            image_base64=req.image_base64,
            image_mime_type=req.image_mime_type,
            images=req.images,
        )
        return {"status": "success", "markdown_question": md}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/solve-direct")
async def solve_direct(req: DirectSolveRequest):
    """Stateless solve of a single question, fully serverless safe."""
    try:
        sol = await call_solver_api(
            markdown_question=req.markdown_question,
            question_num=req.question_num,
            custom_prompt=req.solver_prompt,
        )
        return {"status": "success", "solution": sol}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/upload")
async def upload_batch(
    files: List[UploadFile] = File(...),
    vision_prompt: Optional[str] = Form(None),
    solver_prompt: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Receives screenshots, sets up the job, and starts processing."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    job_id = str(uuid.uuid4())[:8]
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    sorted_files = sorted(files, key=lambda f: f.filename or "")

    question_items: List[QuestionItem] = []
    for idx, uploaded_file in enumerate(sorted_files, start=1):
        filename = uploaded_file.filename or f"screenshot_{idx}.png"
        file_path = job_dir / filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(uploaded_file.file, buffer)

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

    # Background async processing
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


@api.post("/process-item")
async def process_single_item(req: ProcessItemRequest):
    """Processes a single item on demand (vision + solver), ideal for serverless environments."""
    job = JOBS.get(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    target_item = next((it for it in job.items if it.index == req.item_index), None)
    if not target_item:
        raise HTTPException(status_code=404, detail="Item not found")

    try:
        # Stage 1: Vision
        if target_item.status in ["pending", "error"]:
            target_item.status = "transcribing"
            md_q = await call_vision_api(
                target_item.image_path, target_item.index, req.vision_prompt
            )
            target_item.markdown_question = md_q
            target_item.status = "transcribed"
            job.vision_completed = sum(
                1 for it in job.items if it.markdown_question
            )

        # Stage 2: Solver
        if target_item.status == "transcribed":
            target_item.status = "solving"
            sol = await call_solver_api(
                target_item.markdown_question, target_item.index, req.solver_prompt
            )
            target_item.solution = sol
            target_item.status = "completed"
            job.solver_completed = sum(1 for it in job.items if it.solution)

        # Check if all completed
        if all(it.status == "completed" for it in job.items):
            job.status = "completed"
            job.current_message = f"Completed all {job.total_images} questions!"
            job_out_dir = OUTPUT_DIR / req.job_id
            job_out_dir.mkdir(parents=True, exist_ok=True)
            q_file = job_out_dir / "questions.md"
            s_file = job_out_dir / "solutions.md"

            with open(q_file, "w", encoding="utf-8") as f:
                f.write(f"# Exam Questions - Batch {req.job_id}\n\n---\n\n")
                for it in sorted(job.items, key=lambda x: x.index):
                    f.write(f"{it.markdown_question}\n\n---\n\n")

            with open(s_file, "w", encoding="utf-8") as f:
                f.write(f"# Exam Solutions - Batch {req.job_id}\n\n---\n\n")
                for it in sorted(job.items, key=lambda x: x.index):
                    f.write(f"## Question {it.index}\n\n{it.solution}\n\n---\n\n")

            job.questions_md_path = str(q_file)
            job.solutions_md_path = str(s_file)

        return {
            "status": "success",
            "item": {
                "index": target_item.index,
                "filename": target_item.filename,
                "status": target_item.status,
                "markdown_question": target_item.markdown_question,
                "solution": target_item.solution,
            },
            "job_status": job.status,
            "vision_completed": job.vision_completed,
            "solver_completed": job.solver_completed,
        }

    except Exception as e:
        target_item.status = "error"
        target_item.error = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

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


@api.get("/export/{job_id}/{file_type}")
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


# Mount router both at /api and at root for seamless Vercel / Local compatibility
app.include_router(api, prefix="/api")
app.include_router(api)


@app.get("/")
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "SAT Solver Platform API is active"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "sat_solver.server:app", host=config.host, port=config.port, reload=True
    )
