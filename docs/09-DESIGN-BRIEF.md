# 09: Design brief (Person A, Claude Design at the event)

## Recommendation: "Mission control for an agent crew"

**The agent graph is the hero of the screen.** The look is a calm, dark dev-tool aesthetic
(think Linear / Vercel / Raycast), not the old brutalist terminal. The style is projector-safe,
with a light theme available through tokens as a backup.

### Why this direction beats the alternatives

| Option | Verdict |
|---|---|
| **Graph-centric mission control (chosen)** | Judges understand "seven agents" in about 5 seconds because they *see* them. Each demo beat becomes a visual event on the graph: the **rerun grid** filling, the **skip edge** lighting up on a memory hit, the **red barrier** on the patch edge when a guardrail fires, the **loop edge** pulsing when the Critic sends a patch back. Most hackathon dashboards are panels of text, so this one stands out. |
| Plain modern dark dashboard (panels only) | Safe, but the agents become a list. The "crew" story is told in narration instead of shown. |
| Clean light SaaS | Reads well on projectors, but feels like an admin panel. Keep it as a **theme fallback**, not the design. |
| Keep the brutalist terminal | Retired (decision D8). It was strong for the 3-minute video, but dense and hard to read for a live jury. |

### More suggestions (you asked)

1. **A narration line in plain English.** One large sentence of "what's happening now" under the
   graph. Non-technical judges follow along without reading logs. The data is already in the
   contract (`log` events at level `info`).
2. **Verdict ↔ evidence linking.** Hovering the verdict highlights the evidence lines it cites.
   This makes "proof, not guesses" literal.
3. **Run summary end card.** When `done` arrives, show the outcome, time, model calls and sandbox
   runs in large type. It doubles as a natural pause for the presenter.
4. **Cost comparison on a memory hit.** Two tiny bar pairs (time, sandbox runs) comparing #0144
   with #0142. It is the warm-memory proof in one glance.
5. **Restraint styling.** The guardrail-fired moment is the thesis of the demo. Give it the
   strongest visual treatment on the whole screen: the alarm colour, a barrier on the graph edge,
   and a "BLOCKED: would edit a test" label.
6. **One accent, semantic statuses.** Brand green (it's *Greenline*) for identity and
   success/approve, red for fail and guardrail fired, amber for warnings and budget near the cap,
   blue for "active/running". Nothing else.

## Visual constraints (give these to Claude Design)

- Desktop, **1920×1080** primary and 1440×900 must work. Single screen, no page scroll.
- **Dark theme first.** Background is not pure black; use near-black blue-grey. Also produce a light
  token set (same components) for projector fallback.
- Type: one clean sans (e.g. **Inter**, **Geist** or **IBM Plex Sans**) plus one mono (**JetBrains
  Mono** or **Geist Mono**) for evidence, diffs and numbers. Use tabular numerals for counters and
  timers. Minimum sizes: body 15 px, narration 20 px, verdict word 48 px or more.
- Moderate radii (6–10 px), 1 px borders, very subtle elevation. No glassmorphism, no heavy
  gradients, no emoji.
- Motion: only state changes (node activation pulse, edge traversal, evidence row insert, the
  guardrail-fired shake/flash once). Respect reduced-motion.
- Contrast: all text at least WCAG AA against its background, including on a washed-out projector.
- Starting tokens (Claude Design may refine them, but keep the semantic roles):

| Role | Dark | Light |
|---|---|---|
| bg | `#0B0E13` | `#F7F8FA` |
| surface | `#121620` | `#FFFFFF` |
| surface-2 | `#1A1F2B` | `#F0F2F5` |
| border | `#262C3A` | `#DDE1E8` |
| text | `#E7EAF0` | `#0F141C` |
| text-muted | `#8B94A7` | `#5A6475` |
| brand / success | `#2FD27A` | `#139E57` |
| active / info | `#4C8DFF` | `#2563EB` |
| warning | `#F5B83D` | `#B7791F` |
| danger / guardrail | `#FF5A5F` | `#D92D20` |

## Ready-to-paste prompt for Claude Design

> Design a single-screen desktop web app (1920×1080, dark theme with a matching light theme) called
> **Greenline**: an agentic CI-triage "mission control". A failing CI build is investigated live by
> a crew of seven AI agents running on a local model. The screen must let a hackathon jury
> understand, at a glance, which agent is working, what evidence it found, and why the system
> decided to open a fix PR or to escalate to a human.
>
> **Layout:** top bar (logo, "Qwen3-8B · local" model chip, health chips for Model / Memory /
> Sandbox, a LIVE indicator or a RECORDED badge, an elapsed timer, three budget meters for model
> calls, sandbox runs and time as value/cap, and a Scoreboard button). Left column: a list of 6
> failure cases (id like #0142, class chip such as flaky / dependency / env / lint / regression,
> one-line title, last-run outcome pill), plus run options (Budget: Normal/Tight, Mode:
> Live/Recorded) and a Run button. Center (the hero): an **agent graph** of 7 nodes in a
> left-to-right flow: Watcher → Triage → Reproducer → Analyst → Patcher → Critic → Reporter. There
> is a loop edge from Critic back to Patcher, a bypass edge from Triage to Analyst (used when
> Reproducer is skipped thanks to memory), and a place on the Analyst→Patcher edge where a
> guardrail "barrier" appears. Below the graph: a large plain-English narration line, then a
> scrolling evidence feed (commands, observations, citations, each tagged with its agent), with an
> inline **rerun grid** of 10 cells that fill with pass/fail. Right column: a Verdict card (big
> class word, confidence bar, short rationale), a Guardrails list of 5 rules (protected_file,
> diff_cap, no_main_write, no_creds, egress_off), each in one of the states not-checked / clear /
> **BLOCKED**, and an Artifact pane that shows either a Draft PR (title, diff viewer with red/green
> lines, critic votes, body) or an Escalation note (reason chip + text). When a run finishes, show
> a summary end card (outcome, duration, model calls, sandbox runs).
>
> **Mock these states as separate frames:** (1) idle with a case selected; (2) Reproducer
> running, grid 6/10 with 2 failures; (3) memory hit: Reproducer skipped, a "Recalled #0142,
> similarity 0.91" callout with a small cost comparison against #0142; (4) **verdict FLAKY 91%,
> the protected_file guardrail BLOCKED (it would edit a test), escalated to a human**. This is the
> hero frame and the strongest visual moment on screen; (5) patch loop: attempt 1 red and rejected
> by the Critic, attempt 2 running; (6) reported: a green patch, the Critic approved 3/3, the draft
> PR shown; (7) budget exhausted: meters at their cap, "no verdict reached"; (8) backend-offline
> banner; (9) a Scoreboard overlay with metric tiles, a 5×5 confusion matrix and "from N live
> runs".
>
> **Style:** a calm, modern dev-tool aesthetic (Linear/Vercel-like). Near-black blue-grey
> background, one brand green accent, semantic red/amber/blue only for status. Inter-style sans
> plus a monospace for evidence, diffs and numbers, with tabular numerals. Radii of 6–10 px, 1 px
> borders, minimal shadows, no gradients, no glass, no emoji. It must stay readable on a projector
> from 5 metres: body ≥ 15 px, narration ≥ 20 px, verdict ≥ 48 px. Motion only on state changes.

Iterate in Claude Design for **at most about 1.5 hours** (H+0:00 → lock at H+1:45 = 12:45, overlapping
the contract hour; CP1 is at 14:00, D17). Lock the design at 12:45. Polish later comes from code, not new
design rounds.

## Handoff into code

1. Export whatever Claude Design offers: a handoff bundle or code, plus **screenshots of every
   state frame** and the **token list**. Save them in `frontend/design/` (screenshots) and
   `frontend/src/design/tokens.css` (CSS variables, mapped into Tailwind v4 `@theme`).
2. Give Claude Code the screenshots and the spec, **component by component** (`08-FRONTEND-SPEC.md`
   §4), not the whole screen at once: "Implement `GuardrailList` to match `design/state-4.png`,
   reading `RunState.guardrails`".
3. If the export is a prototype in another framework or plain HTML, treat it as a **visual
   reference only**. The component structure and data flow come from `08-FRONTEND-SPEC.md`.
4. Build static first (components with hard-coded props in a dev-only gallery route or a
   `?gallery=1` flag), then wire them to `runStore` after Gate G1.
