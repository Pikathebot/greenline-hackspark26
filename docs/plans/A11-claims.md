# A11 deck: claims ledger

Every number in the pitch deck, its source, and the date it was checked (8 Oct 2026, B's backend,
`GET /api/scoreboard` snapshot of 41 live runs). Re-pull before the final and update both the deck
and this file.

| Slide | Claim | Source |
|---|---|---|
| 6 | 41 live runs | `sampleSize` |
| 6 | Triage accuracy 100%, 39 of 39 verdicts correct | `metrics.triageAccuracy`; matrix diagonal 39 of total 39 |
| 6 | Patch success 100% | `metrics.patchSuccessRate` |
| 6 | Escalation rate 39%, 16 of 41 runs | `metrics.escalationRate` × `sampleSize` |
| 6 | Median to verdict 6.8 s | `metrics.medianTimeToVerdictMs` = 6842 |
| 6 | P95 run duration 20.5 s | `metrics.p95DurationMs` = 20500 |
| 6 | Warm vs cold 12.7 / 13.9 s (#0144 vs #0142) | `metrics.warmVsCold.warmMs` 12657, `coldMs` 13891 |
| 6 | One measured pair, 12 → 1 sandbox runs | Watched live #0142 (12 sandbox runs) then live #0144 (1), similarity 0.86, 8 Oct |
| 6 | Not measured: false-PR rate, human baseline | `notMeasured` |
| 4 | Tight budget: 4 model calls, 3 sandbox runs | App Tight preset (`run.start` caps) |
| 4 | Flaky tests rerun 10 times | `docs/13-DEMO-AND-PITCH.md` (10 for flaky) |
| 2, 4 | Five guardrails by name | `RAIL_ORDER` in `frontend/src/view/consts.ts` |
| 2 | Qwen3-8B, local, no API cost per run | `docs/01-PRODUCT.md`, `docs/02-DECISIONS.md` |

Dropped from the old deck because they were never measured: 88% accuracy, 4.2 vs 38 min, 3.4%
false-PR, 62 s → 11 s, 7 → 3 model calls, 20× reruns, 7.0 GB VRAM. No industry statistics are used.
