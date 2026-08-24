# MASTER PROMPT — Build "Prabhu Sahayogi", a Phase-1 Agentic RAG Assistant for Prabhu Capital (FINAL)

You are a senior AI engineer. Build a production-quality but **minimal-cost Phase-1 agentic RAG virtual assistant** for **Prabhu Capital Limited** (https://www.prabhucapital.com/) — a merchant banking company in Nepal (subsidiary of Prabhu Bank) offering Demat services, Portfolio Management Services (PMS), Registrar to Shares (RTS), Issue Management (IPO/Rights/Debentures), and Mutual Funds/SIP.

## 0. Development environment (respect this exactly)
- A Python venv already exists at `.venv` in the project root — install all dependencies into it. Do NOT create a new environment and do NOT assume conda. Target Python 3.11/3.12.
- The target machine has an **NVIDIA GPU**. Install the **CUDA build of PyTorch FIRST**, before any other package (so sentence-transformers does not pull the CPU-only wheel): `pip install torch --index-url https://download.pytorch.org/whl/cu124` (document this exact step, and the `nvidia-smi` + `torch.cuda.is_available()` verification, in the README).
- **CPU/GPU switching is a hard requirement.** All local model loading (embedder AND reranker) must read a single env var `EMBED_DEVICE` with values `auto` | `cuda` | `cpu`, default `auto` (use cuda if `torch.cuda.is_available()` else cpu). Implement one `resolve_device()` helper in config and pass it everywhere — never hardcode `.to("cuda")` anywhere in the codebase. The same code must run unchanged on a CPU-only server.
- Generate a pinned `requirements.txt` (torch listed with a comment noting the index-url install step).

## 1. Scope of Phase 1
- General Q&A over (a) a small set of supplied PDF documents (company policies, service brochures, fee schedules, forms guidance) and (b) live content from prabhucapital.com.
- NO PII handling, NO authentication, NO role-based access, NO account-specific queries in this phase. If a user asks anything account-specific (their BOID, their allotment, their portfolio), politely direct them to the relevant page (e.g., /ipo-allotment, /boid-search) or the support hotline 015970200.
- English responses; understand and gracefully handle Nepali/romanized-Nepali queries by answering in English (Phase 2: Nepali output).

## 2. Agentic behavior (tool-calling brain)
Implement an agent loop (LlamaIndex Workflows or LangGraph) with these tools. The LLM decides which tool(s) to call per query:

1. `search_documents(query)` — semantic + keyword hybrid search over the indexed PDF corpus and pre-crawled website pages. Returns top chunks with source metadata (doc name / URL, section).
2. `fetch_website(url_or_page)` — live-fetch a whitelisted prabhucapital.com page and extract readable text. Whitelist: pages under prabhucapital.com only. Use this when the question needs FRESH info (latest news/notices, current NAV, new share-registrar announcements, calendar) or when `search_documents` returns low-relevance results.
3. `list_services()` — cheap static tool returning the canonical service catalog with one-line descriptions and page URLs (grounding for navigation questions).

Routing policy:
- Static policy/structure/fee questions → `search_documents` first.
- "Latest / current / today / recent notice" style questions → `fetch_website` on the relevant page (media, calendar, homepage news).
- If retrieval confidence is low after both, say you don't have that information and point to the Information Officer contact — NEVER invent facts, rates, fees, or dates.

## 3. Indexing pipeline (offline, run as a script)
- Parse PDFs with **PyMuPDF (fitz)**; if a PDF is scanned/table-heavy and PyMuPDF output is poor, fall back to **Docling** (open source). Do not use paid parsing APIs.
- Crawl a fixed seed list of prabhucapital.com pages (About, Services: merchant-banking + investment-banking tabs, Downloads, Query pages, Knowledge Center, Contact) with **Crawl4AI or requests+BeautifulSoup**, convert to markdown.
- Chunk with LlamaIndex `SentenceSplitter` (chunk_size≈512 tokens, overlap≈64) but keep tables intact as single chunks in markdown form. Attach metadata: {source, url_or_filename, section_title, doc_type, crawl_or_parse_date}.
- Embed locally via sentence-transformers — no embedding API calls. Default model: **Qwen3-Embedding-0.6B** (GPU is available). CPU fallback model: **BAAI/bge-small-en-v1.5**. Make the model name a config value `EMBED_MODEL` next to `EMBED_DEVICE`; when `EMBED_DEVICE` resolves to `cpu`, default to bge-small. IMPORTANT: the embedding model and the index are coupled — if `EMBED_MODEL` changes, the indexing script must detect the mismatch (store the model name in the Qdrant collection metadata) and refuse to serve / prompt a re-index rather than mixing vectors from two models.
- Store in **Qdrant** (local Docker) with payload metadata; enable both dense vectors and a keyword/BM25 path (Qdrant full-text index on chunk text) and merge results with reciprocal rank fusion.

## 4. Query pipeline (online, per request)
1. If the message is a follow-up turn, rewrite it into a standalone query using the SAME generator LLM with a 1-line rewrite prompt (skip rewriting on first turns / clearly standalone questions).
2. Hybrid retrieve top 20 candidates.
3. Rerank to top 5 with **cross-encoder/ms-marco-MiniLM-L-6-v2** (local), loaded on `resolve_device()` like the embedder. Make the reranker model a config value `RERANK_MODEL` so it can later be upgraded to BGE-reranker-v2-m3 on GPU without code changes.
4. Generate with the generator LLM: temperature 0.2, streaming on. The system prompt must enforce: answer ONLY from provided context/tool results; cite the source (document name or URL) after every factual claim; refuse to guess fees/rates/dates; keep answers concise; include a disclaimer footer like "Prabhu Sahayogi aims to be accurate — please verify important details with Prabhu Capital."
5. Judge gate (see Section 5A for exact rules): run the faithfulness check on the finished answer BEFORE returning it. If verdict is NO → discard the answer and return the safe fallback + contact info instead. Every verdict (pass or fail) is logged.

## 5. LLM choice (least cost)
- Primary generator + rewriter + judge: **Gemini 2.5 Flash via Google AI Studio free tier** (or Flash-Lite).
- Route ALL LLM calls through **LiteLLM** with two named config slots so models can be swapped without code changes:
  - `GENERATOR_MODEL = "gemini/gemini-2.5-flash"`
  - `JUDGE_MODEL = "gemini/gemini-2.5-flash"`  # Phase-1 default; swap to "groq/llama-3.3-70b-versatile" (Groq free tier) for cross-model judging with zero code changes
- Groq free tier (Llama-3.3-70B) is also the fallback provider for dev/testing if Gemini quota is exhausted.

## 5A. LLM-as-Judge — MANDATORY implementation rules
The judge uses the same Gemini Flash model in Phase 1. This is acceptable ONLY because the judge task is objective grounded verification (claims vs. evidence), not subjective quality rating. To keep it safe, the implementation MUST follow all of these rules — do not deviate:

1. **Isolated call.** The judge is a completely separate API call. Its prompt contains ONLY: (a) the retrieved context chunks / tool outputs, and (b) the final answer text. It must NOT include the conversation history, the generator's system prompt, or any indication that the same model produced the answer. The judge sees two pieces of text and compares them — nothing else.
2. **Deterministic and structured.** temperature=0, and force strict JSON output with exactly this schema:
   `{"supported": "YES" | "NO", "unsupported_claims": ["<claim 1>", ...]}`
   Reject/retry once if the output is not valid JSON; on second failure, treat as NO.
3. **Binary question only.** The judge prompt asks exactly one thing: "Is every factual claim in the ANSWER directly supported by the CONTEXT? Answer YES only if all claims are supported. Any claim about fees, rates, dates, or procedures that does not appear in the CONTEXT means NO." Never ask the judge to rate quality, helpfulness, or tone.
4. **Fail closed.** If `supported == "NO"` (or the judge call errors twice), never show the generated answer. Return the safe fallback: a polite message that the assistant cannot confirm that information, plus Prabhu Capital contact details (hotline 015970200, info@prabhucapital.com) and the relevant website link if known.
5. **Log every verdict.** Append to SQLite: {timestamp, session_id, user_query, rewritten_query, retrieved_chunk_ids, answer, judge_json, final_action}. This log is the Phase-2 evaluation dataset.
6. **Human calibration hook.** Provide a tiny CLI script `review_verdicts.py` that samples N logged answers for manual review and records agree/disagree. README must state: if human review disagrees with the judge on >10% of samples, switch `JUDGE_MODEL` to the Groq/Llama slot (cross-model judging) — a config-only change.
7. **Scope guard.** The judge gate runs on every answer that contains factual claims from tools. Pure navigation/small-talk responses (e.g., greetings, "here is the link") may skip the judge but must still be logged.

## 6. UI (chat widget)
Build a mobile-first chat widget (React) resembling a branded assistant:
- Header with assistant name + avatar, green/red Prabhu branding, back button.
- On open: greeting + "Choose an option below for quick assistance" + a grid of 6 category cards. Clicking a card sends a starter question into the chat:
  1. **Demat Services** → "How do I open a Demat account with Prabhu Capital, and what are the charges?"
  2. **Mutual Funds & SIP** → "What mutual fund schemes and SIP options does Prabhu Capital offer?"
  3. **Portfolio Management (PMS)** → "What is Prabhu Capital's Portfolio Management Service and how can I enroll?"
  4. **IPO & Share Issues** → "How can I apply for an IPO through Prabhu Capital, and how do I check share allotment?"
  5. **Share Registrar (RTS)** → "What Registrar to Shares services does Prabhu Capital provide to companies and shareholders?"
  6. **Fees, Forms & Downloads** → "Where can I find Prabhu Capital's forms, and what are the Demat renewal fees?"
- Message input with send button; streaming responses; source citations rendered as small link chips under each answer; persistent disclaimer line at the bottom.
- Keep a session-scoped conversation history (in-memory or SQLite) for follow-up rewriting.

## 7. Explicitly OUT of scope for Phase 1 (do not build)
PII detection/redaction, RBAC, semantic caching, production observability platforms, online judge dashboards, evaluation on logged live traffic, multi-agent planners, fine-tuning.

## 8. Minimal quality gate (build this, it is cheap)
A `golden_set.jsonl` of ~30 real questions (5 per category) with expected source documents. A pytest script that runs the pipeline over the set and reports: retrieval hit-rate (correct source in top 5) and judge pass-rate. Run before every change to chunking/models.

## 9. Tech stack summary
Python 3.11/3.12 in the existing `.venv`, CUDA PyTorch installed first, FastAPI backend (REST + SSE streaming), LlamaIndex (or LangGraph) agent loop, sentence-transformers (Qwen3-Embedding-0.6B on GPU / bge-small-en-v1.5 on CPU, selected via `EMBED_MODEL` + `EMBED_DEVICE=auto|cuda|cpu`), Qdrant local Docker, cross-encoder/ms-marco-MiniLM-L-6-v2 reranker (same device switch, upgradable via `RERANK_MODEL`), Gemini 2.5 Flash free tier via LiteLLM (judge swappable to Groq Llama-3.3-70B by config), React + Tailwind frontend widget, Docker Compose for Qdrant + backend (the frontend may run via Vite dev server locally).

Deliver: repo structure, indexing script, agent/tools code (including the judge module implementing Section 5A exactly), FastAPI endpoints, React widget, golden-set eval script, `review_verdicts.py`, README with run instructions (including the CUDA torch install step and device-switch usage), and a `.env.example` containing: `GEMINI_API_KEY` (required), `GROQ_API_KEY` (optional), `GENERATOR_MODEL`, `JUDGE_MODEL`, `EMBED_MODEL`, `RERANK_MODEL`, `EMBED_DEVICE=auto`.
