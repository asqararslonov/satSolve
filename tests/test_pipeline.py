import pytest
import io
from pathlib import Path
from sat_solver.config import config, UPLOAD_DIR, OUTPUT_DIR
from sat_solver.engine import (
    encode_image,
    call_vision_api,
    call_solver_api,
    process_batch_job,
    JOBS,
    JobStatus,
    QuestionItem,
)
from sat_solver.prompts import DEFAULT_VISION_SYSTEM_PROMPT, DEFAULT_SOLVER_SYSTEM_PROMPT
from fastapi.testclient import TestClient
from sat_solver.server import app


@pytest.fixture
def dummy_image(tmp_path):
    img_file = tmp_path / "test_q1.png"
    # Create a 1x1 simple valid PNG byte sequence
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    img_file.write_bytes(png_bytes)
    return img_file


def test_encode_image(dummy_image):
    b64_data, mime_type = encode_image(dummy_image)
    assert mime_type == "image/png"
    assert len(b64_data) > 0


@pytest.mark.asyncio
async def test_mock_vision_api(dummy_image):
    # When no API key is set, mock response should be returned
    config.openrouter_api_key = ""
    config.anthropic_api_key = ""
    res = await call_vision_api(dummy_image, 1)
    assert "### Question 1" in res
    assert "Visual Description" in res
    assert "Options" in res


@pytest.mark.asyncio
async def test_mock_solver_api():
    config.openrouter_api_key = ""
    config.anthropic_api_key = ""
    sample_q = "### Question 1\nWhat is slope?"
    res = await call_solver_api(sample_q, 1)
    assert "Solution for Question 1" in res
    assert "Final Answer:" in res


@pytest.mark.asyncio
async def test_batch_processing_pipeline(dummy_image):
    job_id = "test_batch_1"
    item = QuestionItem(
        index=1,
        filename="test_q1.png",
        image_path=str(dummy_image),
        status="pending",
    )
    job = JobStatus(job_id=job_id, total_images=1, items=[item])
    JOBS[job_id] = job

    await process_batch_job(job_id)

    assert job.status == "completed"
    assert job.vision_completed == 1
    assert job.solver_completed == 1
    assert item.status == "completed"
    assert "Visual Description" in item.markdown_question
    assert "Final Answer:" in item.solution

    # Check files created
    q_file = Path(job.questions_md_path)
    s_file = Path(job.solutions_md_path)
    assert q_file.exists()
    assert s_file.exists()
    assert "# Exam Questions" in q_file.read_text(encoding="utf-8")
    assert "# Exam Solutions" in s_file.read_text(encoding="utf-8")


def test_fastapi_endpoints():
    client = TestClient(app)

    # Test GET /api/config
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert "ai_provider" in data
    assert "vision_model" in data

    # Test POST /api/config
    res = client.post(
        "/api/config",
        json={"vision_model": "anthropic/claude-3.7-sonnet", "max_concurrency": 5},
    )
    assert res.status_code == 200
    assert res.json()["config"]["max_concurrency"] == 5

    # Test GET /api/prompts
    res = client.get("/api/prompts")
    assert res.status_code == 200
    assert "Visual Description" in res.json()["vision_system_prompt"]

    # Test POST /api/upload
    fake_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    files = [
        ("files", ("q1.png", io.BytesIO(fake_png), "image/png")),
        ("files", ("q2.png", io.BytesIO(fake_png), "image/png")),
    ]
    upload_res = client.post("/api/upload", files=files)
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert "job_id" in upload_data
    assert upload_data["total_files"] == 2

    job_id = upload_data["job_id"]
    job_res = client.get(f"/api/jobs/{job_id}")
    assert job_res.status_code == 200
    assert job_res.json()["total_images"] == 2
