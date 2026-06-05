# AGENT.md — Engineering Command Center

Guidelines for AI coding agents working in this repository.

## Repository Overview

Monorepo with two independently runnable services:

- `backend/` — FastAPI application (Python 3.12, Poetry)
- `frontend/` — Next.js 15 application (TypeScript, npm)
- `docker-compose.yml` — Qdrant vector database (v1.12.4)

## Key Invariants

1. **Never commit `.env` files.** Use `.env.example` as the reference.
2. **API contracts live in `backend/app/schemas/`.** Changing a schema requires updating the corresponding TypeScript types in `frontend/src/types/`.
3. **Backend uses clean architecture:** routes → schemas → services → external clients. Services never import from `api/`.
4. **All new API routes must be registered** in `backend/app/api/v1/router.py`.
5. **Frontend pages live in `src/app/` (App Router).** Client components must have `"use client"` at the top.
6. **The `/chat` route is full-screen** (no sidebar). `AppShell` detects this via `FULL_SCREEN_ROUTES`. If you add more full-screen routes, add them to that set.
7. **All colours use CSS custom properties** (`--bg-primary`, `--text-primary`, etc.), not Tailwind `dark:` variants. See `globals.css`.
8. **UUID5 point IDs** in Qdrant ensure re-indexing is idempotent — do not change the ID scheme (`repo:file_path:chunk_index`).
9. **Semaphore for Gemini rate limiting** in `EmbeddingService` is lazy-initialised (created on first use inside the running event loop). Never move it to `__init__`.

## Services Map

| Service                  | File                                    | Purpose                                |
|--------------------------|-----------------------------------------|----------------------------------------|
| `GeminiService`          | `services/gemini.py`                    | Direct multi-turn chat via Gemini SDK  |
| `GitHubService`          | `services/github.py`                    | List repos, PRs via GitHub REST API    |
| `QdrantService`          | `services/qdrant.py`                    | Vector upsert, search, collection mgmt |
| `EmbeddingService`       | `services/embedding.py`                 | text-embedding-004, async batch embed  |
| `ChunkingService`        | `services/chunker.py`                   | File → chunks (code + prose strategies)|
| `GitHubRepositoryService`| `services/repository_scanner.py`        | Discover, clone, sync org repos        |
| `Retriever`              | `services/retriever.py`                 | Query embed → Qdrant search → chunks   |
| `PromptBuilder`          | `services/prompt_builder.py`            | Assemble RAG prompt with char budget   |
| `RagService`             | `services/rag.py`                       | Full RAG: retrieve → build → generate  |

## Common Commands

### Backend

```bash
cd backend
poetry install                        # install deps
cp ../.env .env                       # needed first time
poetry run python run.py              # start dev server (port 8000)
poetry run python indexer.py --index  # index all org repos into Qdrant
poetry run python indexer.py --stats  # check indexed chunk count
poetry run pytest                     # run tests
poetry run ruff check .               # lint
poetry run mypy app/                  # type check
```

### Indexer CLI

```bash
poetry run python indexer.py --index                  # index all repos
poetry run python indexer.py --index --repo NAME      # index one repo
poetry run python indexer.py --dry-run                # count chunks, no embed
poetry run python indexer.py --stats                  # Qdrant collection stats
poetry run python indexer.py --search "query text"    # test semantic search
poetry run python indexer.py --delete-repo NAME       # remove repo from index
```

### Frontend

```bash
cd frontend
npm install          # install deps
npm run dev          # start dev server (port 3000)
npm run build        # production build
npm run type-check   # tsc --noEmit
npm run lint         # eslint
```

### Infrastructure

```bash
docker compose up -d qdrant    # start vector db
docker compose down            # stop all
docker compose logs qdrant     # view Qdrant logs
```

## Adding a New Feature

1. Define Pydantic schema in `backend/app/schemas/`
2. Implement service logic in `backend/app/services/`
3. Add route handler in `backend/app/api/v1/endpoints/`
4. Register route in `backend/app/api/v1/router.py`
5. Add TypeScript types in `frontend/src/types/`
6. Create React Query hook in `frontend/src/hooks/`
7. Build page in `frontend/src/app/<feature>/page.tsx`
8. Add sidebar entry in `frontend/src/components/layout/Sidebar.tsx`
9. Write tests in `backend/tests/`

## Testing Guidelines

- Unit tests in `backend/tests/`
- Use `httpx.AsyncClient` with `app` for integration tests
- Mock external services (Gemini, GitHub, Qdrant) — never hit real APIs in tests
- `EmbeddingService` tests must mock `google.generativeai` — the semaphore is lazy, so async context is fine
- Minimum coverage target: 80%

## Environment Variables

All required variables are documented in `.env.example`. The backend uses `pydantic-settings` for validation — missing required vars cause a startup crash with a clear error message naming the missing field.

Required for a working local setup:
- `GEMINI_API_KEY`
- `GITHUB_TOKEN`
- `GITHUB_ORG`

## Chunker: Supported File Types

The chunker indexes 84+ extensions including `.py`, `.ts`, `.tsx`, `.go`, `.rs`, `.java`, `.kt`, `.swift`, `.dart`, `.rb`, `.php`, `.cs`, `.cpp`, `.c`, `.sql`, `.graphql`, `.proto`, `.tf`, `.yaml`, `.yml`, `.json`, `.md`, `.ipynb`, and special filenames like `Dockerfile`, `Makefile`, `Jenkinsfile`.

Max file size: 500 KB. Binary files, images, compiled artifacts, and lock files are skipped.
