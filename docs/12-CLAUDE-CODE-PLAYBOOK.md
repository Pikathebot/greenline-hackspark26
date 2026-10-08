# 12: Claude Code playbook

## Principles

1. **Every session starts cold.** A Claude Code session knows only what's in the repo, so this kit
   lives in `docs/` and `CLAUDE.md` points at it. Never rely on "as we discussed".
2. **Plan with the strongest model, implement with the faster one.** Use Opus (plan mode) to break
   a ticket into steps or to debug something nasty. Use Sonnet to implement well-specified tickets.
   It saves usage, which matters over 24 hours on two accounts.
3. **One ticket per session.** Start each ticket with `/clear` (or a new session), paste the
   kickoff prompt, and commit when the acceptance check passes.
4. **Acceptance checks are the definition of done.** Ask Claude Code to *run* the check (pytest,
   curl, vitest, build), not just claim it's done.
5. **If you hit a usage limit:** switch that ticket to your partner's machine only if they're idle.
   Otherwise do manual work (testing, design review, deck) until the limit resets. Front-load heavy
   generation (scaffolding, big components) early, when both accounts are fresh.

## `CLAUDE.md` template (create at H+0:15 at the repo root)

```markdown
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
```

## Kickoff prompts (paste one per ticket; edit the ticket id)

**Contract hour (both, H+0:30).** Person B's session:
> Read CLAUDE.md and docs/04-EVENT-CONTRACT.md. Implement the contract in
> `backend/greenline/events/models.py` (Pydantic v2 discriminated union + TypeAdapter, camelCase
> JSON, exclude_none) and `FailureCase`. Write `backend/tests/test_contract.py` that builds one
> valid instance of every variant and round-trips it. Also write a script that dumps those instances
> to `frontend/src/state/__fixtures__/allVariants.json`. Run the test.

Person A's session:
> Read CLAUDE.md, docs/04-EVENT-CONTRACT.md and docs/08-FRONTEND-SPEC.md §2. Scaffold `frontend/`
> (Vite React TS) if it doesn't exist. Implement `src/contract/events.ts` + `case.ts` exactly as
> specified, then `src/state/reducer.ts` (pure, EMPTY_STATE, run.start resets) and Vitest tests:
> every variant from `__fixtures__/allVariants.json` reduces without throwing, plus one test per
> invariant in §Invariants. Run `npx vitest run`.

**Backend tickets (Person B):**
> Read CLAUDE.md, then docs/05-BACKEND-SPEC.md (focus on §<n>) and docs/10-BUILD-PLAN.md ticket
> **B<k>**. Plan the change first (files, functions, test), then implement it. When done, run the
> ticket's acceptance check and show me the output. Do not change the contract. If something in the
> spec looks wrong, stop and tell me rather than working around it.

**Frontend tickets (Person A):**
> Read CLAUDE.md, docs/08-FRONTEND-SPEC.md §4 (component `<Name>`) and docs/09-DESIGN-BRIEF.md.
> The design reference is `frontend/design/<frame>.png` and the tokens are in
> `src/design/tokens.css`. Implement ticket **A<k>** from docs/10-BUILD-PLAN.md: components read
> RunState from the stores only. First build it with hard-coded props in the `?gallery=1` view,
> then wire it to the store. Run `npm run build` and fix all type errors.

**Debugging (switch to Opus / plan mode):**
> Here's the failing behaviour: <symptom, exact output>. Expected per docs/<file> §<n>: <what>.
> Investigate the root cause before changing code. Show me the evidence (logs, DB rows, SSE output)
> that confirms the cause, then propose the smallest fix.

## Useful habits

- Paste **real output** (stack traces, `curl` output, screenshots of the UI) into the session. It
  beats describing the problem.
- For UI work, give Claude Code a **screenshot of the design frame and a screenshot of the current
  UI** side by side, and ask for the differences to be fixed one by one.
- Use any skills installed on your account where they fit (e.g. frontend-design or dataviz skills
  for the scoreboard, a code-review skill on `backend/greenline/graph/` at G3). Check what's
  available with `/` in Claude Code at setup.
- Commit before letting Claude Code attempt anything large. `git diff` and `git restore` are your
  undo.
- Keep `docs/` read-only during the event, except to record a genuinely new decision in
  `02-DECISIONS.md §D`.

## Git workflow

Moved to **`14-GIT-WORKFLOW.md`** (remote `https://github.com/Pikathebot/greenline-hackspark26`,
HTTPS, `.gitignore` first, commit and push after every ticket, tags at each gate, the pre-move
ritual, and the demo worktree). The two rules that matter most: **`.gitignore` is the first
commit** (the 5 GB model must never be committed), and **never `git add -f`**.
