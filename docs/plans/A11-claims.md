# A11 deck: claims ledger

Every number in the pitch deck, its source, and the date it was checked (8 Oct 2026, B's backend,
`GET /api/scoreboard` snapshot of 112 live runs, taken after B's batch runner finished). Earlier
snapshots of 41 and 70 runs are superseded. Re-pull before the final and update both the deck and
this file.

| Slide | Claim | Source |
|---|---|---|
| 6 | 112 live runs | `sampleSize` |
| 6 | Triage accuracy 100%, 101 of 101 verdicts correct | `metrics.triageAccuracy`; matrix diagonal 101 of total 101 |
| 6 | Patch success 98% | `metrics.patchSuccessRate` = 0.982 |
| 6 | Escalation rate 41%, 46 of 112 runs | `metrics.escalationRate` × `sampleSize` |
| 6 | Median to verdict 6.6 s | `metrics.medianTimeToVerdictMs` |
| 6 | P95 run duration 18.8 s | `metrics.p95DurationMs` |
| 6 | Warm vs cold 11.0 / 14.3 s (#0144 vs #0142) | `metrics.warmVsCold.warmMs`, `coldMs` |
| 6 | Median tool calls 12.0 to 3.0 (older runs mixed in) | `metrics.warmVsCold.coldToolCalls`, `warmToolCalls` |
| 6 | Not measured: false-PR rate, human baseline | `notMeasured` |
| 4 | Tight budget: 4 model calls, 3 sandbox runs | App Tight preset (`run.start` caps) |
| 4 | Flaky tests rerun 10 times | `docs/13-DEMO-AND-PITCH.md` (10 for flaky) |
| 2, 4 | Five guardrails by name | `RAIL_ORDER` in `frontend/src/view/consts.ts` |
| 2 | Qwen3-8B, local, no API cost per run | `docs/01-PRODUCT.md`, `docs/02-DECISIONS.md` |
| 3 notes | #0137 Critic approved 3 of 3 on attempt 1 in the 16 live runs B checked (more have run since) | B's report, 8 Oct |
| 3 notes | Only Critic reject B found: #0139, twice (run-0139-864ea188 rejected 3/3, attempt 2 red, escalated) | B's report, 8 Oct |

Dropped from the old deck because they were never measured: 88% accuracy, 4.2 vs 38 min, 3.4%
false-PR, 62 s to 11 s, 7 to 3 model calls, 20x reruns, 7.0 GB VRAM. No industry statistics are used.
