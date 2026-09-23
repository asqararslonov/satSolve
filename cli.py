#!/usr/bin/env python3
"""
SAT & Exam AI Solver CLI
Batch process exam screenshots into Markdown questions and frontier solutions.
"""

import argparse
import asyncio
from pathlib import Path
import sys
import uuid

from sat_solver.config import config, OUTPUT_DIR
from sat_solver.engine import JOBS, JobStatus, QuestionItem, process_batch_job


async def run_cli(input_dir: str, output_dir: str, provider: str = None):
    in_path = Path(input_dir)
    if not in_path.exists() or not in_path.is_dir():
        print(f"Error: Input directory {input_dir} does not exist.")
        sys.exit(1)

    # Gather images
    valid_exts = {".png", ".jpg", ".jpeg", ".webp"}
    image_files = sorted(
        [p for p in in_path.iterdir() if p.suffix.lower() in valid_exts]
    )

    if not image_files:
        print(f"No image files (.png, .jpg, .webp) found in {input_dir}")
        sys.exit(1)

    print(
        f"==> Found {len(image_files)} screenshots. Starting automated pipeline..."
    )

    if provider:
        config.ai_provider = provider

    job_id = f"cli_{uuid.uuid4().hex[:8]}"
    items = []
    for idx, img in enumerate(image_files, start=1):
        items.append(
            QuestionItem(
                index=idx,
                filename=img.name,
                image_path=str(img),
                status="pending",
            )
        )

    job = JobStatus(
        job_id=job_id,
        total_images=len(items),
        items=items,
    )
    JOBS[job_id] = job

    # Run processing
    print(
        f"==> Stage 1: Transcribing screenshots with Vision Model ({config.vision_model})..."
    )
    await process_batch_job(job_id)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Copy files
    src_q = OUTPUT_DIR / job_id / "questions.md"
    src_s = OUTPUT_DIR / job_id / "solutions.md"

    dst_q = out_path / "questions.md"
    dst_s = out_path / "solutions.md"

    if src_q.exists():
        dst_q.write_text(src_q.read_text(encoding="utf-8"), encoding="utf-8")
        print(f" Saved: {dst_q}")

    if src_s.exists():
        dst_s.write_text(src_s.read_text(encoding="utf-8"), encoding="utf-8")
        print(f" Saved: {dst_s}")

    print("\n Batch processing complete!")


def main():
    parser = argparse.ArgumentParser(
        description="SAT & Exam AI Pipeline: Screenshots to Markdown & Solutions"
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to folder containing screenshots",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="./output",
        help="Path to output folder for .md files",
    )
    parser.add_argument(
        "--provider",
        "-p",
        choices=["openrouter", "anthropic"],
        help="AI Provider",
    )
    args = parser.parse_args()

    asyncio.run(run_cli(args.input, args.output, args.provider))


if __name__ == "__main__":
    main()
