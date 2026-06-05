# Architecture — Engineering Command Center

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                               AWS Lightsail                               │
│                                                                           │
│  ┌───────────────┐    HTTP/JSON    ┌───────────────────────────────────┐  │
│  │  Next.js 15   │ ◄────────────► │         FastAPI Backend            │  │
│  │  (port 3000)  │                │          (port 8000)               │  │
│  └───────────────┘                └───────┬──────────────┬─────────────┘  │
│                                           │              │                 │
│                               ┌───────────▼──┐   ┌──────▼──────────────┐  │
│                               │    Qdrant    │   │    External APIs     │  │
│                               │  (port 6333) │   │  ┌──────────────┐   │  │
│                               │  768-dim     │   │  │ Gemini 2.5   │   │  │
│                               │  COSINE      │   │  │ Flash (LLM)  │   │  │
│                               └──────────────┘   │  ├──────────────┤   │  │
│                                                   │  │ text-embed-  │   │  │
│                                                   │  │ 004 (Embed)  │   │  │
│                                                   │  ├──────────────┤   │  │
│                                                   │  │ GitHub REST  │   │  │
│                                                   │  │ API v3       │   │  │
│                                                   │  └──────────────┘   │  │
│                                                   └─────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────-─┘
```

## Backend Architecture

Clean Architecture with strict layer separation:

```
HTTP Request
     │
     ▼
┌──────────────────────────────────┐
│  API Layer (FastAPI routes)      │  Input validation, HTTP concerns
│  app/api/v1/endpoints/           │
│  chat | github | health |        │
│  knowledge | rag | repositories  │
└────────────────┬─────────────────┘
                 │ Pydantic schemas
┌────────────────▼─────────────────┐
│  Service Layer                   │  Business logic, orchestration
│  app/services/                   │
│  gemini | github | qdrant |      │
│  embedding | chunker | rag |     │
│  retriever | prompt_builder |    │
│  repository_scanner              │
└────────────────┬─────────────────┘
                 │ External SDK calls
┌────────────────▼─────────────────┐
│  External Clients                │  Gemini SDK, GitHub REST, Qdrant gRPC
└──────────────────────────────────┘
```

### Dependency Injection

`app/core/dependencies.py` wires all services via FastAPI's `Depends()`. Services are created per-request. `Settings` is a singleton via `@lru_cache` on `get_settings()`.

### Configuration

`pydantic-settings` reads from environment (`.env` file fallback). Missing required vars fail fast at startup with a descriptive error.

### Logging

`structlog` throughout. Development: coloured human-readable output. Production: JSON lines to stdout (CloudWatch / Datadog compatible).

### Retry

`tenacity` decorates all Gemini and GitHub calls — 3 retries with exponential backoff + jitter.

---

## RAG Pipeline (Primary AI Flow)

```
User question
      │
      ▼
POST /api/v1/rag/chat
      │
      ▼ EmbeddingService.embed_text(task_type="retrieval_query")
Query vector (768-dim)
      │
      ▼ QdrantService.search(query_vector, limit=top_k, repo_filter?)
Top-K scored chunks (ScoredPoint list)
      │
      ▼ Retriever.retrieve()  →  list[RetrievedChunk]
      │
      ▼ PromptBuilder.build(question, chunks)
System prompt + context blocks (≤24K chars, ≤3K chars/chunk)
      │
      ▼ Gemini 2.5 Flash (temperature=0.2, max_tokens=4096)
Answer text
      │
      ▼ RagService assembles RagResponse
{answer, sources, confidence, chunks_retrieved, chunks_used, model}
      │
      ▼
Frontend MessageBubble renders markdown + SourcePanel
```

**Confidence score** = mean cosine similarity of retrieved chunks (0.0–1.0).

**No-context guard**: if 0 chunks are retrieved, returns a canned "I could not find relevant information" response without calling Gemini.

---

## Indexing Pipeline (Offline / CLI)

```
python indexer.py --index
      │
      ▼ GitHubRepositoryService.discover_repositories()
List of repos matching include/exclude globs
      │
      ▼ GitHubRepositoryService.sync_all()  [asyncio.Semaphore(4)]
Clone/pull each repo into REPOS_BASE_PATH via HTTPS+token
      │
      ▼ For each file (matching INDEXABLE_EXTENSIONS, ≤500 KB)
      │
      ▼ ChunkingService.chunk_file()
Code files → sliding window, snapped to def/class boundaries
Prose files → paragraph-boundary accumulation
Each chunk: {content, file_path, language, chunk_index, ...}
      │
      ▼ EmbeddingService.embed_batch(task_type="retrieval_document")
[asyncio.Semaphore(5) for rate limiting, batches of 50]
768-dim vectors
      │
      ▼ QdrantService.upsert_chunks()
UUID5 point IDs (repo:file_path:chunk_index) → idempotent re-index
Payload indexes: repo, language, file_extension (KEYWORD)
Batches of 100 points per upsert call
```

---

## Direct Chat Flow (non-RAG)

```
POST /api/v1/chat  {message, history}
      │
      ▼ GeminiService.chat()
Formats conversation history for Gemini multi-turn API
      │
      ▼ Gemini 2.5 Flash
      │
      ▼ ChatResponse {reply, model, usage}
```

---

## GitHub Data Flow

```
GET /api/v1/github/repos
      │
      ▼ GitHubService.list_repositories()
GitHub REST API /orgs/{org}/repos
Retries up to 3× on transient errors
      │
      ▼ RepositoryListResponse (cached 60s by React Query)
```

---

## Frontend Architecture

Next.js 15 App Router with client/server component split:

```
src/
├── app/              Server components by default (page.tsx per route)
│   ├── chat/         Full-screen RAG chat (no sidebar)
│   ├── health/       Service health dashboard
│   ├── knowledge/    Indexed chunk explorer
│   ├── repositories/ Repo + PR browser
│   ├── rag/          RAG playground
│   └── scanner/      Repo sync control panel
├── components/
│   ├── layout/       AppShell (detects /chat for full-screen), Sidebar, Header
│   ├── chat/         MessageBubble, ChatInput, HistorySidebar, MarkdownContent, SourcePanel
│   ├── rag/          ConfidenceMeter, SourceCard
│   ├── scanner/      SyncResultsDrawer, SyncStateBadge
│   └── ui/           CopyButton, ThemeToggle, LoadingSpinner, ErrorMessage
├── hooks/            React Query hooks — single source of truth per resource
├── lib/              axios instance, queryClient singleton, cn() utility, localStorage history
└── types/            TypeScript interfaces mirroring backend Pydantic schemas
```

**Chat route is full-screen** — `AppShell` detects `/chat` via `usePathname` and skips the sidebar entirely.

**Dark mode** — `next-themes` with `attribute="class"`. CSS custom properties (`--bg-primary`, `--text-primary`, etc.) applied via `.dark` class on `<html>`. All components use CSS vars, not Tailwind dark: variants.

**Chat history** — persisted in `localStorage` under `ecc-chat-history`, capped at 50 sessions. Grouped by Today / Yesterday / This week / Older.

**Markdown rendering** — `react-markdown` + `remark-gfm`. Code blocks use `react-syntax-highlighter` (Prism, `oneDark` / `oneLight` based on resolved theme). Line numbers shown for blocks > 5 lines.

---

## Health Check Strategy

| Endpoint       | Consumer                       | Checks                                |
|----------------|--------------------------------|---------------------------------------|
| `GET /live`    | Container restart probe        | Process alive (always 200)            |
| `GET /ready`   | Load balancer traffic gate     | Qdrant reachable                      |
| `GET /health`  | Monitoring dashboards          | Qdrant + Gemini + GitHub connectivity |

---

## Qdrant Collection Schema

Collection: `engineering_knowledge`

| Field              | Value                    |
|--------------------|--------------------------|
| Distance           | COSINE                   |
| Vector size        | 768                      |
| Embedding model    | text-embedding-004       |
| Point ID type      | UUID5 (deterministic)    |

Payload structure per point:
```json
{
  "content": "...",
  "file_path": "src/auth/middleware.py",
  "repo": "payments-service",
  "language": "python",
  "file_extension": ".py",
  "chunk_index": 3,
  "total_chunks": 12,
  "commit_sha": "abc123"
}
```

Keyword indexes on `repo`, `language`, `file_extension` enable filtered search.

---

## Deployment — AWS Lightsail

Recommended topology:
- 1× Lightsail instance (4 vCPU, 8 GB RAM) running Docker Compose
- Caddy reverse proxy: `ecc.yourdomain.com` → Next.js (3000) + FastAPI (8000)
- Persistent Docker volume for Qdrant data
- GitHub Actions CI/CD: lint → test → SSH deploy

Environment variables are set as instance-level env vars, not committed to the repository.
