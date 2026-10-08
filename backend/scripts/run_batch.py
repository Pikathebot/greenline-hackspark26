"""B12: scripts/run_batch.py --cases all --times 3

Drives the REAL running backend over HTTP (POST .../runs, then reads the
SSE stream to done) -- the same path a human clicking "Run" takes. Builds
real run history for /api/scoreboard and candidates for
export_demo_runs.py. This is what actually builds history overnight
(ticket B14); this ticket (B12) just builds the tool.

Needs the backend (+ Docker + the model server) already running.

Run from backend/:
    .venv\\Scripts\\python.exe scripts\\run_batch.py --cases all --times 3
    .venv\\Scripts\\python.exe scripts\\run_batch.py --cases 0142,0144 --times 5 --reset-before 0142
"""

from __future__ import annotations

import argparse
import json
import time

import httpx

from greenline.graph.cases import all_case_ids

STREAM_TIMEOUT_S = 180.0


def _start_run(client: httpx.Client, case_id: str, budget: str) -> str:
    for attempt in range(2):
        resp = client.post(f"/api/cases/{case_id}/runs", json={"mode": "live", "budget": budget})
        if resp.status_code == 409 and attempt == 0:
            time.sleep(1)  # the run manager's active-run lock can lag a moment after done
            continue
        resp.raise_for_status()
        return resp.json()["runId"]
    resp.raise_for_status()  # pragma: no cover - unreachable, satisfies type checkers
    raise RuntimeError("unreachable")


def _stream_until_done(client: httpx.Client, run_id: str) -> dict:
    with client.stream("GET", f"/api/runs/{run_id}/stream", timeout=STREAM_TIMEOUT_S) as resp:
        for line in resp.iter_lines():
            if not line.startswith("data:"):
                continue
            event = json.loads(line[len("data:") :].strip())
            if event["type"] == "done":
                return event
    return {"outcome": "timeout"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="http://127.0.0.1:8000")
    parser.add_argument("--cases", default="all")
    parser.add_argument("--times", type=int, default=3)
    parser.add_argument("--budget", default="normal", choices=["normal", "tight"])
    parser.add_argument(
        "--reset-before",
        default="",
        help="comma-separated case ids to reset memory before each run of (so a batch can "
        "measure both a cold case and the warm one that follows it, docs/05 §10)",
    )
    args = parser.parse_args()

    cases = all_case_ids() if args.cases == "all" else args.cases.split(",")
    reset_before = {c for c in args.reset_before.split(",") if c}

    results: list[dict] = []
    with httpx.Client(base_url=args.host, timeout=30) as client:
        for round_n in range(1, args.times + 1):
            for case_id in cases:
                if case_id in reset_before:
                    client.post("/api/admin/reset-memory")

                run_id = _start_run(client, case_id, args.budget)
                started = time.monotonic()
                done = _stream_until_done(client, run_id)
                elapsed = time.monotonic() - started
                outcome = done.get("outcome", "unknown")
                print(f"[{round_n}/{args.times}] {case_id}: {outcome} ({elapsed:.1f}s, {run_id})")
                results.append(
                    {"case_id": case_id, "round": round_n, "run_id": run_id, "outcome": outcome}
                )

    outcome_counts: dict[str, int] = {}
    for r in results:
        outcome_counts[r["outcome"]] = outcome_counts.get(r["outcome"], 0) + 1
    print(f"\n{len(results)} runs across {len(cases)} case(s) x {args.times} round(s).")
    print("Outcomes:", outcome_counts)


if __name__ == "__main__":
    main()
