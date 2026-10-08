# Greenline: HackSpark'26 Build Kit

**Event:** HackSpark'26 finale, 24-hour build, 8 → 9 October 2026. **Real schedule (D17):** start
11:00 · **Checkpoint 1 at 14:00** · selection 16:00 · move venue 16:15 · **evaluation 2 from 18:00** ·
**final evaluation 07:30 on 9 Oct** (so ~20 h of usable build time). See `10-BUILD-PLAN.md`.
**Repo:** `https://github.com/Pikathebot/greenline-hackspark26` (empty, private) · `14-GIT-WORKFLOW.md`.
**Team:** 2 people, 2 laptops, 2 Claude Code accounts.
**Goal:** rebuild Greenline from an empty repo during the event, so it is better than the
pre-event prototype, and demo it live.

This kit holds specs, contracts and decisions only. It has **no implementation code**, and that
is deliberate: event rules say everything is created at the event, so all code is written fresh
there with Claude Code. The kit exists so neither of you spends event hours re-deciding things
that are already decided.

---

## How to use this kit at the event

1. **H+0:** each person reads `00-README.md` (this file), `02-DECISIONS.md` and their own track in
   `10-BUILD-PLAN.md`. That takes about 15 minutes.
2. **H+0:** run the environment check on both laptops (`11-SETUP-CHECKLIST.md` §4). Tools and
   model weights are **pre-staged before the event** in the working folder `D:\greenline\backend\models\` (D15), so nothing
   big needs downloading at the venue.
3. **H+0:15:** turn `D:\greenline\` into the repo. **The first commit is `.gitignore`**, so the
   5 GB model can never be committed (`14-GIT-WORKFLOW.md`). Then copy this
   whole `hackathon-kit/` folder into it as `docs/`,
   and create `CLAUDE.md` from the template in `12-CLAUDE-CODE-PLAYBOOK.md`.
4. **H+0:30 → H+1:30:** write the event contract together, from `04-EVENT-CONTRACT.md`. Once
   it's written, freeze it. This is the only hour where both of you work on the same file.
5. After that, each person runs their track from `10-BUILD-PLAN.md` using the kickoff prompts in
   `12-CLAUDE-CODE-PLAYBOOK.md`. Meet at each **gate**.

## Files

| File | What it is | Who needs it |
|---|---|---|
| `00-README.md` | This index | Both |
| `01-PRODUCT.md` | What Greenline is, the problem, the six demo cases and the beat each one proves | Both |
| `02-DECISIONS.md` | Locked decisions, what changed since the prototype, and **lessons from 32 real runs** | Both, read first |
| `03-ARCHITECTURE.md` | Processes, ports, two-machine topology, repo layout, request lifecycle | Both |
| `04-EVENT-CONTRACT.md` | The frozen `GreenlineEvent` union (v2), invariants, `RunState`, wire format | Both, written together at H+0:30 |
| `05-BACKEND-SPEC.md` | API, DB, emitter, bus, sandbox, LLM client, memory, guardrails, agent graph, demo mode | Backend (Person B) |
| `06-FIXTURE-REPO-SPEC.md` | `ledger-core`: the seeded broken repo with six branches, each with a defect | Backend |
| `07-MODEL-RUNTIME.md` | `llama-server`, Qwen3-8B, flags, VRAM, thinking-off, troubleshooting | Backend |
| `08-FRONTEND-SPEC.md` | Screen IA, state, SSE client, components, interactions, empty/error states | Frontend (Person A) |
| `09-DESIGN-BRIEF.md` | The visual direction, a ready-to-paste Claude Design prompt, and the handoff into code | Frontend |
| `10-BUILD-PLAN.md` | 24-hour schedule, two tracks, tickets with acceptance criteria, gates, cut list | Both |
| `11-SETUP-CHECKLIST.md` | Pre-event staging (what's allowed, what isn't), installs, verification commands | Both, **before the event** and at H+0 |
| `12-CLAUDE-CODE-PLAYBOOK.md` | `CLAUDE.md` template, kickoff prompts, session hygiene, git workflow | Both |
| `14-GIT-WORKFLOW.md` | The GitHub remote, push cadence, tags per gate, the pre-move ritual, demo worktree, recovery | Both, **before the event** and H+0:15 |
| `13-DEMO-AND-PITCH.md` | Demo script, pre-demo checklist, failure playbook, judge Q&A, deck claims to re-measure | Both, from CP1 (14:00) |

## The three sentences everyone must be able to say

1. A red CI build goes in. Greenline **reproduces it in a locked-down Docker sandbox** to prove the
   cause, then either opens a **draft fix PR** or **escalates to a human with evidence**.
2. It's a graph of seven small agents on a **local 8B model**: no code leaves the laptop and the
   per-run cost is ₹0. Five guardrails and a hard budget mean it **can say "no"**.
3. Every agent step is a typed event streamed live to the dashboard, so the jury **watches the
   reasoning happen** instead of taking it on trust.

## What's different from the prototype (summary)

Details are in `02-DECISIONS.md`.

- **Frontend redesigned from scratch** in Claude Design: an agent-graph-centric "mission control"
  instead of the brutalist terminal look.
- **No replay UI.** Scrubbing, rate control, the transport bar, frontend fixtures, `?replay` and
  `?live` are all gone. The UI has **one** code path: a live SSE stream.
- **Backend "demo mode"** is the only safety net. It re-streams a real recorded run through the
  same SSE path, and the UI always labels it **RECORDED**.
- **Fixes for what failed live last time:** the lint fix is tool-first, the regression patcher
  gets the breaking commit and the failing test, confidence comes from evidence, rerun counts
  adapt to the class, the flake rate is tuned so it reliably shows up, and budget exhaustion can
  be demonstrated with an honest "tight budget" switch.
