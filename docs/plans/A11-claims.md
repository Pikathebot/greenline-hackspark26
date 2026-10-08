# A11 deck: claims ledger

Every number in the pitch deck, its source, and the date it was checked (8 Oct 2026, B's backend,
`GET /api/scoreboard` snapshot of 70 live runs, the figures B confirmed). An earlier snapshot of 41
runs came from a different run database and is not used. Re-pull before the final and update both
the deck and this file.

| Slide | Claim | Source |
|---|---|---|
| 6 | 70 live runs | `sampleSize` |
| 6 | Triage accuracy 100%, 64 of 64 verdicts correct | `metrics.triageAccuracy`; matrix diagonal 64 of total 64 |
| 6 | Patch success 97% | `metrics.patchSuccessRate` = 0.971 |
| 6 | Escalation rate 43%, 30 of 70 runs | `metrics.escalationRate` × `sampleSize` |
| 6 | Median to verdict 6.4 s | `metrics.medianTimeToVerdictMs` |
| 6 | P95 run duration 19.8 s | `metrics.p95DurationMs` |
| 6 | Warm vs cold 11.0 / 13.8 s (#0144 vs #0142) | `metrics.warmVsCold.warmMs`, `coldMs` |
| 6 | Median tool calls 11.5 to 3.0 (older runs mixed in) | `metrics.warmVsCold.coldToolCalls`, `warmToolCalls` |
| 6 | Not measured: false-PR rate, human baseline | `notMeasured` |
| 4 | Tight budget: 4 model calls, 3 sandbox runs | App Tight preset (`run.start` caps) |
| 4 | Flaky tests rerun 10 times | `docs/13-DEMO-AND-PITCH.md` (10 for flaky) |
| 2, 4 | Five guardrails by name | `RAIL_ORDER` in `frontend/src/view/consts.ts` |
| 2 | Qwen3-8B, local, no API cost per run | `docs/01-PRODUCT.md`, `docs/02-DECISIONS.md` |
| 3 notes | #0137 Critic approved 3 of 3 on attempt 1 in all 16 live runs | B's report, 8 Oct |
| 3 notes | Only Critic reject: #0139, twice (run-0139-864ea188 rejected 3/3, attempt 2 red, escalated) | B's report, 8 Oct |

Dropped from the old deck because they were never measured: 88% accuracy, 4.2 vs 38 min, 3.4%
false-PR, 62 s to 11 s, 7 to 3 model calls, 20x reruns, 7.0 GB VRAM. No industry statistics are used.
