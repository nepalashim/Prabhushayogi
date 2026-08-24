# Prabhu Sahayogi

A Phase-1 agentic RAG chat assistant for [Prabhu Capital Limited](https://www.prabhucapital.com/) — answers
general questions about Demat services, Portfolio Management (PMS), Registrar to Shares (RTS), Issue
Management (IPO/Rights/Debentures), and Mutual Funds/SIP, grounded in indexed PDFs and the live website,
with a mandatory LLM-as-judge faithfulness check before any answer is shown.

## Quick Start (run backend + frontend)

Everything below assumes you're in the project root, `.env` is filled in (see [Environment Setup](#environment-setup)),
and dependencies are installed (see [First-Time Setup](#first-time-setup)).

**1. Start Qdrant** (if not already running):

```powershell
docker compose up -d qdrant
```

**2. Start the backend** (FastAPI, port 8000):

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Wait for `Application startup complete.` — the first startup loads the embedder/reranker onto the GPU, which
takes a few seconds. Verify with:

```powershell
curl http://127.0.0.1:8000/api/health
```

**3. Start the frontend** (Vite dev server, port 5173), in a separate terminal:

```powershell
cd frontend
npm run dev
```

Open **http://localhost:5173** in a browser. The chat widget is a circular launcher button in the
bottom-right corner — click it to open the panel.

**To stop:** Ctrl+C both terminals; `docker compose down` to stop Qdrant (data persists in `data/qdrant_storage/`).

---

## First-Time Setup (fresh clone, from scratch)

### Prerequisites

- Python 3.13 (`python --version`)
- An NVIDIA GPU + driver (optional but recommended — CPU works too, just slower for embedding/reranking)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Qdrant)
- [Node.js](https://nodejs.org/) 20+ (for the frontend)
- [Git](https://git-scm.com/)

### Clone the repo

```powershell
git clone <your-repo-url>
cd prabhucapital
```

### Create the virtual environment

The repo does not ship a `.venv` (it's gitignored — see [Pushing to GitHub](#pushing-to-github)). Create
one locally before anything else:

```powershell
python -m venv .venv
```

### Install Python dependencies

Run the install script — it handles the CUDA-torch-first ordering correctly (see the comments in
`scripts/install_deps.ps1` for why plain `pip install -r requirements.txt` alone is NOT safe here):

```powershell
.\scripts\install_deps.ps1
```

This installs `requirements.txt`, then swaps in the CUDA build of torch matching whatever version got
resolved, runs `crawl4ai-setup` (downloads a Chromium binary for the web crawler), and finishes by running
`scripts/verify_gpu.py` so you can confirm `torch.cuda.is_available() == True`.

### Install frontend dependencies

```powershell
cd frontend
npm install
```

### Environment Setup

If `.env` doesn't exist yet, copy it from the template and fill in `GEMINI_API_KEY`
(**skip this if `.env` already exists** — running `copy` again overwrites it and wipes out any key
you've already set):

```powershell
if (-not (Test-Path .env)) { copy .env.example .env }
```

Get a **free** Gemini API key (no credit card required) at **https://aistudio.google.com/apikey** — sign in,
accept the Terms of Service, and a key is generated for you automatically. Paste it in as `GEMINI_API_KEY=...`.

> **Switching to Claude later:** the `.env.example` has a commented-out Claude block. Once you have an
> Anthropic API key (a separate, pay-per-token product from console.anthropic.com — not the same thing as a
> claude.ai Pro/Max subscription), set `ANTHROPIC_API_KEY` and uncomment the three `anthropic/claude-...`
> model lines to override the Gemini defaults. No code changes needed — this is a config-only swap by design.

The frontend also needs its own `.env` (default already points at `http://localhost:8000`, so this is
usually a no-op) — same caveat, skip if it already exists:

```powershell
cd frontend
if (-not (Test-Path .env)) { copy .env.example .env }
cd ..
```

### Verify the GPU (optional, already run by install_deps.ps1)

```powershell
.venv\Scripts\python.exe scripts\verify_gpu.py
```

### Build the search index

Before the assistant can answer anything, it needs an index. Drop any real PDFs (fee schedules, service
brochures, policy documents) into `data/raw_pdfs/` — this is optional; the indexer also crawls the live
website regardless of whether any PDFs are present:

```powershell
.venv\Scripts\python.exe -m indexing.run_index
```

**Adding PDFs later?** Just drop them into `data/raw_pdfs/` and re-run the same command — chunk IDs are
content-addressable, so this safely adds the new content without disturbing or duplicating what's already
indexed. `--force-rebuild` is only needed if you change `EMBED_MODEL`/`EMBED_DEVICE` in a way that changes the
embedding dimension — the indexer refuses to mix vectors from two different models into one collection
(see `indexing/index_meta.py`).

---

## Containerized backend (production / Linux deployment only)

Local dev runs the backend natively (see Quick Start above) so GPU access just works without WSL2 +
NVIDIA Container Toolkit friction. For a Linux host or a CPU-only deployment target, a `Dockerfile.backend`
and a `prod` Compose profile are provided — gated behind that profile so a plain `docker compose up` never
builds or starts it:

```powershell
docker compose --profile prod up -d --build
```

This builds the backend image (CPU torch by default; pass `--build-arg TORCH_INDEX_URL=...` for a CUDA
build on a GPU-enabled Linux host — see the comments in `Dockerfile.backend`) and runs it alongside Qdrant,
reaching it via the Compose network's `qdrant` DNS name instead of `localhost` (a config-only override, no
code change). Not build-tested on this Windows dev machine — built per the same documented two-step torch
install pattern as `scripts/install_deps.ps1`.

## Device switching (CPU / GPU)

Everything reads a single `EMBED_DEVICE` setting in `.env`: `auto` (default, uses CUDA if available),
`cuda`, or `cpu`. `EMBED_MODEL` auto-picks `Qwen/Qwen3-Embedding-0.6B` on GPU or `BAAI/bge-small-en-v1.5` on
CPU unless set explicitly. The same code runs unchanged either way — see `config/settings.py::resolve_device()`.

## LLM model configuration

All LLM calls go through LiteLLM, routed via three config slots in `.env` (`GENERATOR_MODEL`, `JUDGE_MODEL`,
`REWRITE_MODEL`) plus an optional `GROQ_FALLBACK_MODEL` for resilience if the primary provider has an
outage. Currently defaults to the free Gemini tier, split across two different `-lite` models for the judge
and rewriter (each gets its own separate free-tier daily quota bucket) — see the comments in `.env.example`.

## Running tests

```powershell
# Pure-logic unit tests (RRF, chunker, whitelist, judge JSON parsing) - fast, no external services needed
.venv\Scripts\python.exe -m pytest tests -v

# Golden-set retrieval hit-rate (free, no LLM calls - needs Qdrant + an index)
.venv\Scripts\python.exe -m pytest eval\test_golden_set.py -k hit_rate -v

# Golden-set judge pass-rate (uses real LLM API quota - opt in explicitly)
$env:RUN_LLM_EVAL="1"; .venv\Scripts\python.exe -m pytest eval\test_golden_set.py -k judge_pass_rate -v
```

## Judge calibration

Periodically sample logged judge verdicts and record whether you agree with them:

```powershell
.venv\Scripts\python.exe -m eval.review_verdicts --n 20 --reviewer your-name
```

If disagreement exceeds 10%, the tool reminds you to switch `JUDGE_MODEL` to the Groq fallback slot for
cross-model judging — a config-only change.

## Environment variables reference

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | — | Free-tier Google AI Studio key (required to generate/judge/rewrite) |
| `ANTHROPIC_API_KEY` | — | Optional, for switching to Claude later |
| `GROQ_API_KEY` | — | Optional, cross-provider fallback |
| `GENERATOR_MODEL` | `gemini/gemini-3.5-flash-lite` | Answers user questions |
| `JUDGE_MODEL` | `gemini/gemini-3.1-flash-lite` | Faithfulness verification (Section 5A) |
| `REWRITE_MODEL` | `gemini/gemini-3.1-flash-lite` | Follow-up query rewriting |
| `GROQ_FALLBACK_MODEL` | `groq/llama-3.3-70b-versatile` | Used only if the primary call fails and `GROQ_API_KEY` is set |
| `EMBED_DEVICE` | `auto` | `auto` \| `cuda` \| `cpu` |
| `EMBED_MODEL` | *(auto-picked)* | Override to pin a specific embedding model |
| `RERANK_MODEL` | `cross-encoder/ms-marco-MiniLM-L6-v2` | Reranker model |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant connection |
| `QDRANT_COLLECTION_NAME` | `prabhu_chunks` | Qdrant collection name |
| `SQLITE_DB_PATH` | `data/app.db` | Conversation/verdict log |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated list of allowed frontend origins |
| `MAX_TOOL_ITERATIONS` | `4` | Cap on agent tool-calling rounds per turn |

## Repository layout

- `config/` — settings, device resolution, Qdrant client, static reference data (contacts, service catalog, crawl seed list)
- `ml_models/` — device-aware embedder/reranker wrappers
- `indexing/` — offline pipeline: PDF parsing, web crawling, chunking, embedding, Qdrant loading
- `retrieval/` — hybrid (dense + keyword) search with Reciprocal Rank Fusion
- `llm/` — LiteLLM routing + shared prompt text
- `agent/` — the tool-calling agent loop (LlamaIndex Workflows)
- `judge/` — the LLM-as-judge faithfulness gate
- `query_logging/` — SQLite conversation/verdict audit trail
- `app/` — the FastAPI backend (SSE chat endpoint + health check)
- `eval/` — the golden-set quality gate and human calibration CLI
- `frontend/` — the React + Vite + Tailwind chat widget
- `tests/` — unit tests for pure/isolated logic

## Out of scope for Phase 1

PII detection/redaction, authentication/RBAC, semantic caching, production observability platforms,
multi-agent planners, fine-tuning. No account-specific data is ever handled — questions about a user's own
account, allotment, or portfolio are redirected to the relevant self-service page or the support hotline.

## Pushing to GitHub

### What `.gitignore` already excludes (never gets pushed)

- `.venv/` — recreate it locally with `python -m venv .venv` + `scripts\install_deps.ps1` (see above); it's
  large and platform-specific, so it doesn't belong in git.
- `.env` — **contains your real `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` / etc.** Only `.env.example`
  (no real values) is tracked. Double-check `git status` never shows `.env` as staged before you commit.
- `data/qdrant_storage/`, `data/app.db`, `data/index_meta.json`, `data/crawled_pages/*`, `data/raw_pdfs/*` —
  generated/local data, rebuilt by `indexing/run_index.py`. Only the `.gitkeep` placeholders are tracked.
- `frontend/node_modules/`, `frontend/dist/` — reinstalled via `npm install`, rebuilt via `npm run build`.
- `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `*.log` — local build/debug artifacts.

Before your first commit, double-check nothing unwanted slipped in:

```powershell
git status
```

Anything listed under "Untracked files" or "Changes to be committed" that matches the patterns above means
`.gitignore` needs a closer look — fix that before committing, don't just `git add -A` blindly.

### First push (repo has no commits yet)

1. Create a new **empty** repository on GitHub (no README/license/gitignore — this project already has
   its own) — e.g. `github.com/new`.
2. From the project root:

```powershell
git add .
git status   # sanity-check the file list one more time before committing
git commit -m "Initial commit: Prabhu Sahayogi Phase-1 agentic RAG assistant"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

After that, `git push` alone is enough for future commits.

### Cloning it again elsewhere

Anyone (including you, on another machine) can now stand this project back up from nothing but the pushed
repo by following [First-Time Setup](#first-time-setup-fresh-clone-from-scratch) above end to end: clone →
create `.venv` → `install_deps.ps1` → `npm install` → fill in `.env` → `docker compose up -d qdrant` →
`indexing.run_index` → run backend + frontend (see [Quick Start](#quick-start-run-backend--frontend)).
