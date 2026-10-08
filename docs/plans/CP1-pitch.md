# Greenline CP1 pitch (14:00, about 2.5 min)

Draft built from what was verified on 8 Oct 2026.

## Script

| Time | On screen | Say (paraphrase, don't read) |
|---|---|---|
| 0:00-0:20 | Idle dashboard, case #0142 selected | "A red build stops a team, and most of the time goes on *why* it failed, not on fixing it. Greenline is seven AI agents on a **local** model. It reproduces the failure in a sealed sandbox and proves the cause before it touches anything." |
| 0:20-0:35 | Live llama call (curl or the llama-server page) | "That's the model, running on this laptop. Nothing leaves the machine." |
| 0:35-1:35 | Recorded #0142 (`1`, `D`, `Enter`) | **Say first:** "This is a real run we recorded, replayed through the same event stream. The badge says RECORDED. The live backend is running now, and we'll show it later." Point at the graph lighting up. At the rerun grid: "10 reruns in fresh containers, no network. 3 failed, so it's flaky, proven rather than guessed." At the red barrier: "The only fix would edit a test. Greenline never edits tests to make them pass, so it escalates to a human with the evidence." |
| 1:35-1:50 | Final state, then `E` | "24 seconds, 3 model calls, 11 sandbox runs. The verdict is computed from the evidence, and one keypress exports the report." |
| 1:50-2:30 | Architecture slide | See below. |
| 2:30-2:45 | Plan slide (or say it) | See below. |

## Architecture slide (one slide, one diagram)

Left to right: **CI failure -> LangGraph, 7 agents on one local Qwen3-8B -> Docker sandbox -> verdict -> draft PR or escalation**.

Three callouts:
1. **One event contract:** every step is a typed event streamed over SSE to the UI. The UI is a pure reducer over those events, so a recorded run and a live run use the same path.
2. **Five guardrails:** `protected_file`, `diff_cap`, `no_main_write`, `no_creds`, `egress_off`. Any of them can veto.
3. **Sandbox:** fresh container per run, network off, empty environment, resource limits.

## Plan for the next 5 hours

- Now: the live backend works for #0142 and #0137, including the patcher and critic.
- Next: the memory skip (#0142 then #0144) and the scoreboard with measured numbers.
- By 18:00: live runs on the demo path, with RECORDED as the fallback.

## Honesty checks

- Don't claim "a third of the time" or any warm-versus-cold figure. #0144 memory isn't built (B10).
- Don't claim accuracy percentages. The scoreboard (B12) doesn't exist yet.
- Safe numbers: 7 pass / 3 fail, 24.0s, 3 model calls, 11 sandbox runs, FLAKY 95%.
- Say "10 reruns", not the old deck's "20x".

## Likely CP1 questions (answers in docs/13-DEMO-AND-PITCH.md)

- Why a local model?
- What if the model is wrong?
- Is running AI-proposed code dangerous?

## To settle before 14:00

1. Confirm whether the CP1 slot is 2 or 3 minutes.
2. Decide how to show the live llama call: curl, or the llama-server page on B's machine (10.10.17.224).
