import asyncio
import base64
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from sat_solver.config import config, OUTPUT_DIR
from sat_solver.prompts import (
    DEFAULT_VISION_SYSTEM_PROMPT,
    DEFAULT_SOLVER_SYSTEM_PROMPT,
)


class QuestionItem(BaseModel):
    index: int
    filename: str
    image_path: str
    status: str = "pending"  # pending, transcribing, transcribed, solving, completed, error
    markdown_question: str = ""
    solution: str = ""
    error: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: str = "idle"  # idle, processing_vision, processing_solver, completed, failed
    total_images: int = 0
    vision_completed: int = 0
    solver_completed: int = 0
    current_message: str = "Ready"
    items: List[QuestionItem] = Field(default_factory=list)
    questions_md_path: Optional[str] = None
    solutions_md_path: Optional[str] = None
    error: Optional[str] = None


# In-memory storage for jobs
JOBS: Dict[str, JobStatus] = {}


def encode_image(image_path: str | Path) -> tuple[str, str]:
    """Returns (base64_string, mime_type)"""
    path = Path(image_path)
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        mime_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"

    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return encoded, mime_type


async def call_vision_api(
    image_path: Optional[str | Path] = None,
    question_num: int = 1,
    custom_prompt: Optional[str] = None,
    image_base64: Optional[str] = None,
    image_mime_type: Optional[str] = None,
) -> str:
    """Call multimodal model via Omni Route, OpenRouter, or Anthropic to transcribe screenshot to Markdown."""
    provider = config.ai_provider.lower()
    api_key = config.get_api_key(provider)
    system_prompt = custom_prompt or DEFAULT_VISION_SYSTEM_PROMPT
    model = config.vision_model

    # If no API key is provided, return structured mock response
    if not api_key:
        await asyncio.sleep(0.8)
        return (
            f"### Question {question_num}\n\n"
            f"**Question Text:**\n"
            f"In the coordinate plane below, line $l$ has an $x$-intercept of $(4, 0)$ and a $y$-intercept of $(0, -2)$. "
            f"What is the slope of line $l$?\n\n"
            f"#### Visual Description\n"
            f"- **Figure Type**: Cartesian Coordinate Plane\n"
            f"- **Key Elements**:\n"
            f"  - $x$-axis and $y$-axis with integer grid marks from $-5$ to $5$.\n"
            f"  - Line $l$ passes through points $(4, 0)$ on the positive $x$-axis and $(0, -2)$ on the negative $y$-axis.\n"
            f"  - The line slopes upward from left to right with a positive slope.\n\n"
            f"**Options:**\n"
            f"- **A)** $-\\frac{{1}}{{2}}$\n"
            f"- **B)** $\\frac{{1}}{{2}}$\n"
            f"- **C)** $2$\n"
            f"- **D)** $-2$\n"
        )

    if image_base64:
        b64_data = image_base64
        mime_type = image_mime_type or "image/png"
    elif image_path:
        b64_data, mime_type = encode_image(image_path)
    else:
        raise ValueError("Either image_path or image_base64 must be provided")

    async with httpx.AsyncClient(timeout=180.0, verify=False) as client:
        if provider == "anthropic":
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": model,
                "max_tokens": 3000,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": b64_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": f"Transcribe this screenshot for Question {question_num}. Follow all instructions and format with LaTeX math and detailed visual description.",
                            },
                        ],
                    }
                ],
            }
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

        else:
            # Omni Route or OpenRouter
            if provider == "omniroute":
                url = config.omni_route_url
            else:
                url = "https://openrouter.ai/api/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Transcribe this screenshot for Question {question_num}. Follow all instructions and format with LaTeX math and detailed visual description.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64_data}"
                                },
                            },
                        ],
                    },
                ],
            }
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


async def call_solver_api(
    markdown_question: str,
    question_num: int,
    custom_prompt: Optional[str] = None,
) -> str:
    """Call frontier reasoning model (Claude Opus / Frontier) to solve the question."""
    provider = config.ai_provider.lower()
    api_key = config.get_api_key(provider)
    system_prompt = custom_prompt or DEFAULT_SOLVER_SYSTEM_PROMPT
    model = config.solver_model

    # Mock response if no API key provided
    if not api_key:
        await asyncio.sleep(1.0)
        return (
            f"### Solution for Question {question_num}\n\n"
            f"**Analysis & Derivation:**\n"
            f"1. We are given two points on line $l$: the $x$-intercept $(4, 0)$ and the $y$-intercept $(0, -2)$.\n"
            f"2. The slope formula between any two points $(x_1, y_1)$ and $(x_2, y_2)$ is:\n"
            f"   $$m = \\frac{{y_2 - y_1}}{{x_2 - x_1}}$$\n"
            f"3. Substituting $(x_1, y_1) = (0, -2)$ and $(x_2, y_2) = (4, 0)$:\n"
            f"   $$m = \\frac{{0 - (-2)}}{{4 - 0}} = \\frac{{2}}{{4}} = \\frac{{1}}{{2}}$$\n\n"
            f"**Verification:**\n"
            f"- Using the slope-intercept equation $y = mx + b$ with $b = -2$:\n"
            f"  $$y = \\frac{{1}}{{2}}x - 2$$\n"
            f"- Testing point $(4, 0)$: $y = \\frac{{1}}{{2}}(4) - 2 = 2 - 2 = 0$. This confirms the point lies on the line.\n\n"
            f"**Final Answer:**\n"
            f"**Final Answer: (B) $\\frac{{1}}{{2}}$**\n"
        )

    async with httpx.AsyncClient(timeout=180.0, verify=False) as client:
        if provider == "anthropic":
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Please solve this exam question step-by-step with full rigor:\n\n{markdown_question}",
                    }
                ],
            }
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

        else:
            # Omni Route or OpenRouter
            if provider == "omniroute":
                url = config.omni_route_url
            else:
                url = "https://openrouter.ai/api/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Please solve this exam question step-by-step with full rigor:\n\n{markdown_question}",
                    },
                ],
            }
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


async def process_batch_job(
    job_id: str,
    vision_prompt: Optional[str] = None,
    solver_prompt: Optional[str] = None,
):
    """Orchestrates the two-stage pipeline for a batch of screenshots with concurrency."""
    job = JOBS.get(job_id)
    if not job:
        return

    semaphore = asyncio.Semaphore(config.max_concurrency)

    # ==========================================
    # STAGE 1: Parallel Vision Extraction
    # ==========================================
    job.status = "processing_vision"
    job.current_message = f"Transcribing {job.total_images} screenshots into Markdown with visual descriptions..."

    async def transcribe_item(item: QuestionItem):
        async with semaphore:
            item.status = "transcribing"
            try:
                md_q = await call_vision_api(
                    item.image_path, item.index, vision_prompt
                )
                item.markdown_question = md_q
                item.status = "transcribed"
                job.vision_completed += 1
            except Exception as e:
                item.error = f"Vision error: {str(e)}"
                item.status = "error"

    await asyncio.gather(*(transcribe_item(item) for item in job.items))

    # Compile questions.md
    job_out_dir = OUTPUT_DIR / job_id
    job_out_dir.mkdir(parents=True, exist_ok=True)
    questions_file = job_out_dir / "questions.md"

    with open(questions_file, "w", encoding="utf-8") as f:
        f.write(f"# Exam Questions - Batch {job_id}\n\n")
        f.write(f"Total Questions Transcribed: {job.total_images}\n\n---\n\n")
        for item in sorted(job.items, key=lambda x: x.index):
            f.write(f"{item.markdown_question}\n\n---\n\n")

    job.questions_md_path = str(questions_file)

    # ==========================================
    # STAGE 2: Automated Cloud Frontier Solver
    # ==========================================
    job.status = "processing_solver"
    job.current_message = f"Dispatching questions to cloud frontier AI ({config.solver_model})..."

    async def solve_item(item: QuestionItem):
        if item.status == "error":
            return
        async with semaphore:
            item.status = "solving"
            try:
                sol = await call_solver_api(
                    item.markdown_question, item.index, solver_prompt
                )
                item.solution = sol
                item.status = "completed"
                job.solver_completed += 1
            except Exception as e:
                item.error = f"Solver error: {str(e)}"
                item.status = "error"

    await asyncio.gather(*(solve_item(item) for item in job.items))

    # Compile solutions.md
    solutions_file = job_out_dir / "solutions.md"
    with open(solutions_file, "w", encoding="utf-8") as f:
        f.write(f"# Exam Solutions & Explanations - Batch {job_id}\n\n")
        f.write(f"Model: {config.solver_model}\n\n---\n\n")
        for item in sorted(job.items, key=lambda x: x.index):
            f.write(f"## Question {item.index}\n\n")
            f.write(f"### Problem Stem\n{item.markdown_question}\n\n")
            f.write(f"### Frontier AI Solution\n{item.solution}\n\n---\n\n")

    job.solutions_md_path = str(solutions_file)
    job.status = "completed"
    job.current_message = f"Completed! Processed {job.total_images} questions."
