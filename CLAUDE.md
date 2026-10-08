# Greenline: working conventions (HackSpark'26 build)

Read this first, then the relevant file in docs/. docs/ is the full spec; decisions in
docs/02-DECISIONS.md are final. Don't re-litigate them, raise conflicts instead.

## What this is
Agentic CI triage. A red build → 7-agent LangGraph on a local Qwen3-8B (llama-server) → Docker
sandbox reproduction → verdict → draft PR or escalation. Every step is a typed GreenlineEvent
streamed over SSE to a React UI. Live only, no replay UI. Backend demo mode re-streams a REAL
recorded run and the UI labels it RECORDED.

## Hard rules
1. The contract (frontend/src/contract/*.ts ⇄ backend/greenline/events/models.py) is frozen after
   gate G0. Additive changes only, in both languages in the same commit.
2. Every run emits run.start first and exactly one done last. t is stamped only by RunEmitter
   (monotonic). Any exception → error event → done{outcome:'error'}.
3. Frontend run state = pure reducer over events. Components read RunState from stores; no
   component holds run data; no fixture/demo event data in frontend/src (except reducer test JSON).
4. Never hardcode outcomes, verdicts or event sequences per case in graph code. Case config =
   branch, failing test node id, patch target file, fallback CI log only. Ground-truth class is for the scoreboard
   only.
5. Sandbox: fresh container per run, network_disabled=True, environment={}, resource limits, always
   removed in finally (retry once, log, never raise).
6. Model calls: llama-server json_schema response_format, flat Pydantic schemas, one global
   asyncio lock, thinking disabled at server start.
7. GREENLINE_DRY_RUN=true by default. Never push to main/master in the fixture repo or anywhere.
8. Windows: PowerShell for scripts; Docker via the Python SDK (not shell); write files with \n.

## Layout
backend/  FastAPI app (greenline/), scripts/, tests/, demo_runs/, models/ (5 GB GGUFs: gitignored,
          never read, move, commit or `git add -f` them)
frontend/ Vite React TS app (src/contract, state, api, components, design)
docs/     the build kit: 00-README.md is the index

## Commands
backend:  .venv\Scripts\activate · uvicorn greenline.main:app --host 0.0.0.0 --port 8000 · pytest
frontend: npm run dev · npx vitest run · npm run build
model:    backend\scripts\llama-server.ps1 · backend\scripts\llama-embed.ps1

## Definition of done for any ticket
Its acceptance check in docs/10-BUILD-PLAN.md passes, and you ran it (not assumed). Commit message
starts with the ticket id.
