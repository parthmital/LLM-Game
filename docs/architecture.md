# Codebase Architecture

## Context

The Obsidian Flask is a two part local game application:

- `Backend/` is a FastAPI service that owns session lifecycle, event persistence, deterministic world state, memory retrieval, prompt assembly, LLM calls, validation, and WebSocket updates.
- `Frontend/` is a Vite React application that owns routing, UI state, HTTP calls, WebSocket connection state, and presentation.

The repository uses a pragmatic layered architecture rather than a package split. The main goal is to keep gameplay rules, side effects, transport code, and UI concerns easy to find and test without introducing a framework on top of the existing frameworks.

## Folder And Module Rules

Backend dependency flow:

- `schemas/` contains canonical Pydantic data models and must not import runtime layers.
- `core/` contains deterministic persistence and reducer logic. It may import `schemas/` and standard library modules only.
- `game/` contains game specific loading and validation. It may import `schemas/`.
- `memory/` contains embedding and FAISS adapters. It may import `config`.
- `llm/` contains provider and prompt adapters. It may import `schemas/`, `memory/`, and `config`.
- `graph/` composes one turn from input through retrieval, prompt, LLM generation, validation, commit, and output. It may import backend runtime layers but must not import `api/`.
- `api/` contains HTTP and WebSocket transport, API schemas, session lifecycle, and API response presenters.

Frontend dependency flow:

- `contracts/` contains backend DTOs in snake case. It must not import React, stores, or services.
- `services/httpClient.ts` owns REST transport.
- `services/websocket.ts` owns WebSocket lifecycle and reconnect behaviour.
- `services/api.ts` is a compatibility facade for callers that need the public client, WebSocket service, or API DTOs.
- `stores/` owns client state and maps backend DTOs into UI domain types.
- `pages/` owns route level composition.
- `components/game/` and `components/layout/` own reusable UI for the game shell.
- `components/ui/` contains generic shadcn style primitives.
- `types/game.ts` contains UI domain types only, not backend DTOs.

## Data Flow

Normal action flow:

1. UI calls `useGameStore.sendAction`.
2. `APIClient` posts to `POST /api/game/action/{session_id}`.
3. The route asks `SessionManager` to process the action.
4. `SessionManager` invokes the compiled LangGraph for that session.
5. The graph retrieves memories, builds a prompt, calls Groq, parses JSON, validates world updates, commits valid events, updates short term memory, updates FAISS memory, and periodically saves per session snapshots.
6. The route appends display dialogue, broadcasts WebSocket updates, saves the session, and returns `ActionResponse`.
7. The frontend refreshes state and maps backend DTOs into UI state.

Direct state mutation flow:

- Movement, clue linking, pickup, and drop endpoints create explicit events, apply the reducer, save the auto snapshot, and return a fresh `GameStateResponse`.

Persistence flow:

- Event history lives in each session directory under `Backend/data/sessions/{session_id}/events.db`.
- Auto and manual snapshots are separate JSON files in the same session directory.
- Dialogue history is persisted alongside snapshots.
- FAISS index and metadata are also scoped to the session directory.

## Extension Points

- New event type: add it to `schemas/events.py`, validate it in `game/validator.py`, reduce it in `core/reducer.py`, expose any response shape in `api/schemas.py` and `api/presenters.py`, then add focused tests.
- New API endpoint: add the route in `api/routes.py`; keep response mapping in `api/presenters.py` when it adapts internal state.
- New backend DTO: add it to `api/schemas.py` and mirror the client shape in `Frontend/src/contracts/api.ts`.
- New frontend workflow: place server calls in `services/`, state transitions in `stores/`, route composition in `pages/`, and repeated controls in `components/`.
- New prompt input: add canonical state or memory formatting in `llm/prompt_builder.py`; keep validation in code, not only in prompt instructions.

## Failure Handling

- FastAPI routes return `HTTPException` for expected client and session errors.
- Unhandled backend exceptions are logged server side. Response details are hidden by default and only exposed when `DEBUG_ERRORS=true`.
- LLM JSON parse failures produce fallback dialogue and no world mutations.
- Invalid LLM world updates are dropped and returned as validation errors.
- Session actions are guarded by a per session async lock.
- WebSocket clients receive generic error messages for engine failures and are removed from the session on disconnect or send failure.

## Security

- `GROQ_API_KEY`, `SESSION_SECRET`, `.env`, generated data, and local caches are ignored by git.
- CORS origins are explicit through `CORS_ORIGINS`; avoid wildcard origins when credentials are enabled.
- Vite dev server defaults to `localhost`; set `VITE_DEV_HOST` only when LAN access is intended.
- Player input and LLM output are untrusted. World mutations must pass `game/validator.py` before `core/reducer.py` applies them.
- The prompt instructs the model not to create entities, but the validator is the enforcement boundary.
- There is still no authentication, authorisation, or rate limiting. Do not expose this backend on an untrusted network as is.

## Operations

Local checks:

```powershell
.\check.ps1
```

Manual checks:

```powershell
python -m compileall Backend
python -m unittest discover -s Backend\tests
cd Frontend
npm run typecheck
npm run lint
npm run test
npm run build
```

Startup:

```powershell
.\start.ps1
```

Runtime signals:

- `GET /health` reports backend readiness for the frontend boot gate.
- `GET /api/game/health` reports API readiness, active session count, and LLM reachability.
- Backend logs include method, path, status, and latency.

## Validation

Architecture rules are enforced by:

- `Backend/tests/test_architecture.py` for backend layer import direction and graph side effect boundaries.
- TypeScript type checks for frontend contracts and service boundaries.
- ESLint for frontend import, React hook, and refresh constraints.
- Vitest for frontend HTTP client behaviour.
- `npm audit` for JavaScript dependency advisories.
