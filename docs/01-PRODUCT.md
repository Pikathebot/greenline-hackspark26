# 01: Product

## One-liner

**Greenline: proof, not guesses, for red builds.** It is a crew of AI agents that takes a failing
CI build, re-runs it in a sealed sandbox to *prove* the cause, and then either opens a draft fix PR
or escalates to a human with evidence.

## The problem

- A red CI build stops the whole team. Most of the time goes on working out *why* it failed, not
  on fixing it.
- Engineers re-run jobs, scroll logs and guess. Is it a flaky test, a broken dependency,
  environment drift, a lint slip, or a real regression?
- Existing AI tools jump straight to a patch, even when the right answer is "don't touch this".
  An eager patch to a flaky test hides the flake. An eager patch to a missing env var hides a
  deployment gap.

## The solution, and the three pillars from the pitch deck

| Pillar | What it means concretely |
|---|---|
| **Proof before action** | The failure is reproduced N times, each time in a fresh disposable Docker container, before any verdict is given. The pass/fail distribution is the evidence. |
| **Restraint by design** | Five guardrails can veto a patch. Escalating to a human is a first-class outcome, not a failure. Greenline **never edits tests to make them pass**. |
| **Fully local and private** | Runs on an 8 GB laptop GPU (Qwen3-8B via `llama-server`). No code or logs leave the machine, and the API cost per run is ₹0. |

## Five failure classes

| Class | Meaning | Typical right answer |
|---|---|---|
| `flaky` | Intermittent, timing- or order-dependent | **Escalate** with the rerun distribution. Never "fix" by editing the test. |
| `dependency` | Import or symbol error tied to a version/pin | Patch the import site or roll back the pin |
| `env` | Missing environment configuration (env var, service) | **Escalate**. A code patch would mask a deployment gap. |
| `lint` | Static analysis fails, tests pass | Mechanical fix (formatter/linter autofix) |
| `regression` | Deterministic failure from a logic change | Patch the logic, verified green in the sandbox |

## The seven agents (graph nodes)

| Node | Role | Uses the model? | Uses the sandbox? |
|---|---|---|---|
| **Watcher** | Picks up the red build: checks out the branch and runs CI once to capture the real log | no | 1 run |
| **Triage** | Classifies into one of the 5 classes and checks memory for a similar past failure | 1 call | no |
| **Reproducer** | Re-runs the failing test N times, N adapted to the class (skipped on a warm memory hit) | no | N runs |
| **Analyst** | Reads the evidence and gives the verdict, with confidence *computed from evidence* | 1 call | no |
| **Patcher** | Proposes a minimal fix (tool-first for lint) and runs the guardrails before applying it | 0–2 calls | 1 run |
| **Critic** | Deterministic checks plus k-sample self-consistency vote, loops back to Patcher once if rejected | 0–3 calls | no |
| **Reporter** | Writes a draft PR body or an escalation note | 1 call | no |

Graph shape: `watcher → triage → reproducer (skips itself on a warm memory hit or a lint case) →
analyst → (reporter if blocked | patcher) → critic → (patcher, max 2 attempts | reporter)`. Any
budget exhaustion goes straight to `reporter`.

## The six demo cases: each one earns a distinct beat

The cases live as branches in the seeded test repo `ledger-core` (`06-FIXTURE-REPO-SPEC.md`). The
case IDs are display IDs.

| Case | Class | Expected outcome | The beat it proves |
|---|---|---|---|
| **#0142** | flaky | **escalated**, because `protected_file` fires (the fix would edit a test) | **Hero case, restraint.** About 10 sandbox reruns show a genuinely mixed pass/fail distribution. Greenline *could* patch the test, but refuses and escalates with proof. |
| **#0144** | flaky (warm) | escalated, same guardrail | **Memory.** Same root-cause *shape* as #0142 in a different file. Triage recalls #0142, Reproducer is **skipped**, and the run is about 3× faster with 0 sandbox reruns. Run it right after #0142. |
| **#0139** | dependency | **reported** (draft PR) | **Happy path.** Renamed symbol → one-line import fix → green in the sandbox → Critic approves → PR. |
| **#0131** | lint | reported (draft PR) | **Budget scales down.** Tool-first fix (`ruff --fix`) with zero model calls for the patch. The cheapest run of the six. |
| **#0137** | regression | reported (draft PR), possibly after a Critic loop | **Patch → critique → re-patch.** The Patcher sees the breaking commit and the failing test. If attempt 1 is red, the Critic rejects and attempt 2 follows. |
| **#0128** | env | escalated ("no safe automated fix"), or **budget_exhausted** under the Tight budget preset | **Honest limits.** A missing env var can't be patched safely. With the Tight budget it runs out mid-investigation and *says so* instead of guessing. |

## Target users and benefits (from the deck)

- **Developers** get a clear cause and evidence instead of an hour of re-running jobs and reading
  logs.
- **Teams** get flaky tests flagged rather than blindly "fixed", and routine breaks arriving as
  ready-to-review PRs.
- **Organisations** lose less time to red builds, send no code to third-party AI, and keep a full
  audit trail. Every run is a persisted event log.

## Non-goals (do not build at the event)

- Auth, multi-tenancy, real CI webhooks. A case is assumed already detected, and the case list is
  static.
- Non-Python target repos. Horizontal scaling: one GPU means one model queue.
- Mobile or responsive layout. Desktop only (1920×1080 and 1440×900).
- Replay UI: no scrubbing, no rate control, no frontend fixtures. See `02-DECISIONS.md`.
- Real GitHub PRs by default. `DRY_RUN=true`; a live draft PR is an optional stretch.
