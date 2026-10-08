# 13: Demo and pitch

The judging format is unknown (D14), so prepare a **3-minute** and a **6-minute** version of the
same story, live first, with fallbacks.

## Checkpoint pitches (D17)

| Checkpoint | Clock | Length | What to show | Honesty note |
|---|---|---|---|---|
| **CP1** | 14:00 | assume 2–3 min (confirm) | The one-line problem, then the **designed UI** playing the demo-mode #0142 run, the 7-agent graph, the guardrail barrier, and one **live** llama call (curl or the llama-server page) as proof that the model is local. Then: architecture slide, plan for the next 5 hours. | Badge says RECORDED; say "this is a recorded run through the same stream, live backend arrives this evening". |
| **CP2** | 18:00+ | rolling; be ready for 3 and for 10 min | #0142 **live** if G2 made it, then #0144 memory skip if it exists. If not: RECORDED + whatever live part works. | Never imply recorded = live. Say what is done and what is next. |
| **Final** | 07:30 | the 3/6-minute scripts below | Full script, all six cases, scoreboard. | Numbers come from `/api/scoreboard`, not memory. |

For CP2 run the demo from the pinned worktree (`10-BUILD-PLAN.md`, `14-GIT-WORKFLOW.md` §6), not
from the folder where you are still building. Have the 30 s, 2 min and 6 min versions ready, because
rolling evaluation means the time you get is not the time you were told.

## Fallback ladder (decide in seconds, on stage)

| Level | When | What |
|---|---|---|
| **A: Live** (default) | `/api/health` all green at T-5 min | Real runs, real model, real sandbox |
| **B: Live on the spare** | The 5070 laptop misbehaves (driver, Docker, thermal) | Swap HDMI to the 4060 laptop, which runs the identical stack |
| **C: Recorded** | Model or Docker down on both, or the slot is too short for live runs | Toggle Mode → Recorded (`D`). The **RECORDED** badge is visible, and you **say it out loud**: "this is a real run we recorded an hour ago, replayed through the same stream". |
| **D: Video** | Laptop or projector failure | Play the backup video (recorded by 05:45, stored on both laptops + USB) |

Honesty rule: never let the jury believe a recorded run is live. It costs nothing to say, and
being caught costs everything.

## Pre-demo checklist (T-15 min)

1. Power plugged in, Best-performance mode, notifications off, Chrome/Discord closed
   (`11-SETUP-CHECKLIST.md` §6).
2. Start in order: Docker Desktop, then `llama-server.ps1`, then `llama-embed.ps1`, then uvicorn,
   then `npm run dev` (or `npm run build && npm run preview`). Run `check_env.ps1`: all green.
3. `docker ps -a`: no leftover containers (`docker container prune -f` if there are).
4. **Warm the GPU:** run #0131 once (it's fast). The first model call after a cold start is slower.
5. **Memory state:** `POST /api/admin/reset-memory`, then run #0142 once live, so memory holds a
   fresh #0142 trace and #0144 will hit. (Or keep the overnight memory, since it already has
   #0142 traces. Decide during rehearsal and stay consistent.)
6. `GET /api/cases`: every case has a `lastRun`, so the case list looks alive and the cost
   comparison has data.
7. Browser full screen, zoom 100%, scoreboard closed, case #0142 selected, Budget **Normal**,
   Mode **Live**.
8. Backup video open in a paused player on the second screen or a background window.

## 3-minute script

| Time | On screen | Say (paraphrase, don't read) |
|---|---|---|
| 0:00–0:20 | Idle dashboard | "A red build stops a whole team, and most of the time goes on *why*, not on fixing it. Greenline is a crew of seven AI agents on a local model that **proves** the cause before it touches anything." |
| 0:20–1:10 | **#0142 live** (`1`, `Enter`) | Point at the graph lighting up. When the rerun grid fills: "it re-runs the failing test ten times, each in a fresh sealed container. No network, no secrets. **3 of 10 failed**: that's a flaky test, proven, not guessed." At the guardrail: "it *could* patch this, but the fix would edit a test, and **Greenline never edits tests to make them pass**. So it escalates to a human, with the evidence." |
| 1:10–1:35 | **#0144 live** (`2`, `Enter`) | "A different test with the same failure shape. It **remembers** #0142, skips reproduction entirely, and finishes in about a third of the time." Point at the cost comparison. |
| 1:35–2:15 | **#0139 live** (`3`, `Enter`) | "The happy path: a dependency renamed a symbol. The Patcher fixes the import, the sandbox goes green, the Critic votes, and we get a **draft PR**, never a push to main." Point at the diff and the votes. |
| 2:15–2:40 | **#0128 Tight** (`6`, `T`, `Enter`) | "And when it can't finish, it says so. With a tight budget it stops mid-investigation and escalates, with no silent failure and no guess." |
| 2:40–3:00 | Scoreboard (`S`) | "Across N live runs today: triage accuracy X%, median time to verdict Y seconds, ₹0 per run, and no code ever left this laptop." |

## 6-minute script

Same as above, plus:
- **#0131** after #0139 (30 s): "Lint doesn't need an LLM at all. The linter's own autofix makes
  the patch, so this is the cheapest run."
- **#0137** (60–90 s): "A real logic regression. The Patcher reads the commit that broke it and the
  failing test as the spec." If attempt 1 went red: "the Critic rejected it, and attempt two is
  green". If it went green first try, just say that. Don't fake a loop.
- 30 s on the architecture: the graph, the event stream, the "every step is a typed event" seam,
  local model on an 8 GB GPU.

## Deck claims to re-measure before pitching (from the pre-event deck)

| Deck claim | Status | Replace with |
|---|---|---|
| "Failures are reproduced up to 20× in a fresh Docker container" | Event build uses **10** for flaky, 3 for deterministic classes | "reproduced 10× in fresh containers" |
| "62s → 11s run time, repeat flaky test" | Fixture numbers. The live prototype was ~30 s → ~10 s | Median #0142 vs #0144 from `/api/scoreboard` `warmVsCold` |
| "7 → 3 model calls" | Live: 3 → 3 model calls; **sandbox runs 11 → 1** is the real saving | "11 → 1 sandbox runs" (measured) |
| "88% triage accuracy, 4.2 vs 38 min, 3.4% false-PR, <90 s p95" | Labelled illustrative; came from invented data | Measured triage accuracy, p95 duration, median time to verdict. **Drop** false-PR rate and the human baseline (not measured) or cite them clearly as external targets. |
| "6/6 demo cases run end to end on real infrastructure" | True only if G3 passed | Keep if true |
| "7.0 GB measured VRAM … RTX 4060" | Re-check on the 5070 | `nvidia-smi` reading at demo time |
| "₹0 per-run API cost" | True (local model) | Keep |

Is the old `Greenline-HackSpark26.pptx` allowed at the event? If the rules forbid pre-made material,
rebuild the deck at 05:00 from this kit (slide outline below). If it's allowed, just update the
numbers.

**Slide outline (7 slides):** 1. Title / team · 2. Problem → solution + three pillars · 3. The
7-agent graph + tech stack · 4. Guardrails, budget, one event contract · 5. Live demo (switch to
the app) · 6. Measured results (scoreboard numbers + warm vs cold) · 7. Impact, who benefits,
what's next.

## Likely judge questions (short, honest answers)

| Q | A |
|---|---|
| Why a local model instead of GPT/Claude? | Privacy (source code never leaves the company), ₹0 per run, and it runs on a normal 8 GB laptop GPU. The guardrails and sandbox matter more than raw model IQ for this job. |
| What if the model is wrong? | It never acts on its own say-so. Verdicts come from sandbox evidence, confidence is computed from that evidence, patches must go green in the sandbox **and** pass the Critic, the output is only ever a *draft* PR, and five guardrails can veto. |
| Isn't running AI-proposed code dangerous? | It runs in a container with no network, no credentials, a read-only source copy, CPU/RAM/time limits, and a fresh container every time. |
| Why not just auto-retry flaky tests? | Retrying hides the flake. We *measure* it (3/10), tell a human, and refuse to "fix" it by editing the test. |
| How does it plug into real CI? | Today a case is pre-detected. Next is a GitHub Actions / webhook trigger feeding the same graph. The UI and event contract don't change. |
| How did you measure accuracy? | Six seeded failure cases with known ground truth, N live runs each, computed by the backend from the event log. A small sample, and we say so on screen. |
| Scale? | One GPU means one queue, by design. Scale out with more GPU workers behind the same event contract. |
| What's next? | Real CI webhooks, more languages, learning from accepted/rejected PRs to measure the false-PR rate for real. |

## After the demo

Tag `v1.0`, push, and write the README (quick start, architecture diagram, demo GIF) if the
submission needs it. A good final ticket for Claude Code: "write README.md from docs/00, 03 and 13,
for a judge who will clone the repo".
