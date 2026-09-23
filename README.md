# SAT & Exam AI Platform

Automated end-to-end platform for transcribing batches of 20–30 exam screenshots into structured Markdown (`questions.md`) with mathematical visual descriptions and solving them using frontier cloud reasoning AI (`solutions.md`).

---

## Features

- **Batch Ingestion**: Upload 20–30 screenshots at once (.png, .jpg, .webp) with drag-and-drop support and automatic natural sorting.
- **Visual Transcription Engine**: Multimodal AI (Claude 3.7 Sonnet / OpenRouter Vision) extracts:
  - Exact question text and options.
  - Math converted to standard LaTeX (`$...$` inline, `$$...$$` block).
  - Dedicated **Visual Description** protocol for geometry, graphs, tables, and coordinate systems.
- **Frontier Cloud Solver**: Automatically dispatches extracted Markdown to frontier reasoning models (Claude Opus / Claude 3.7 Sonnet with extended thinking) to produce rigorous step-by-step proofs, sanity verifications, and bold final answers.
- **Asynchronous Parallel Processing**: Multi-worker queue with rate-limit protection (processes 20–30 screenshots concurrently in 30–45 seconds).
- **Interactive Web Dashboard**:
  - Live progress tracking for Stage 1 (Vision) and Stage 2 (Frontier Solver).
  - Side-by-side verification: Original Screenshot $\leftrightarrow$ Transcribed Markdown $\leftrightarrow$ Frontier AI Solution.
  - Live LaTeX math rendering with KaTeX.
  - One-click export of `questions.md` and `solutions.md`.
- **Headless CLI**: Run the entire pipeline directly from the command line.

---

## Quick Start

### 1. Activate Environment & Install Dependencies

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy `.env.example` to `.env` or set your keys in the Web UI Settings:

```bash
cp .env.example .env
```

Set your keys:
- **OpenRouter** (Omni-route): Set `OPENROUTER_API_KEY=sk-or-v1-...` and `AI_PROVIDER=openrouter`
- **Anthropic Direct**: Set `ANTHROPIC_API_KEY=sk-ant-api03-...` and `AI_PROVIDER=anthropic`

---

## Running the Web Dashboard

Start the FastAPI server:

```bash
source .venv/bin/activate
python -m sat_solver.server
```

Open your browser at:
`http://localhost:8000`

1. Drag and drop 20–30 screenshots.
2. Click **Run Automated Pipeline**.
3. Watch real-time progress for Vision Transcription and Frontier Cloud Solving.
4. Review side-by-side and click **Download questions.md** and **Download solutions.md**.

---

## Running via CLI (Headless Automation)

To process a folder containing screenshots without opening a browser:

```bash
source .venv/bin/activate
python cli.py --input ./my_screenshots --output ./my_results
```

Generated files:
- `./my_results/questions.md`
- `./my_results/solutions.md`

---

## Running Tests

```bash
source .venv/bin/activate
PYTHONPATH=. pytest -v
```
