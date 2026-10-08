# Greenline: commands cheat sheet

Run from `D:\greenline` in PowerShell unless a section says `backend\` or `frontend\`.
Docker Desktop must be running. `$py` below means `.\.venv\Scripts\python.exe` (from `backend\`).

## Start / stop
```powershell
.\start.bat                      # model, embeddings, API, UI; opens http://localhost:5173
.\stop.ps1                       # kill whatever listens on 8080, 8081, 8000, 5173
backend\scripts\check_env.ps1    # health check; every line should be [OK]
```
Start the pieces by hand (one window each):
```powershell
cd backend; .\scripts\llama-server.ps1        # model, :8080 (wait for "server is listening")
cd backend; .\scripts\llama-embed.ps1         # embeddings, :8081
cd backend; .venv\Scripts\activate; uvicorn greenline.main:app --host 0.0.0.0 --port 8000
cd frontend; npm run dev                      # UI, :5173
```

## First-time setup (a new laptop)
```powershell
git pull
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
docker build -t greenline-sandbox:latest greenline/sandbox   # sandbox image
python scripts\seed_repo.py                                   # local fixture repo (add --force to rebuild)
cd ..\frontend; npm ci
```
Models go in `backend\models\` (copy from the USB drive, never commit): `Qwen3-8B-Q4_K_M.gguf`, `bge-small-en-v1.5-q8_0.gguf`.
`frontend\.env.local`: `VITE_API_TARGET=http://127.0.0.1:8000` (this laptop) or B's laptop IP.

## Run cases from the terminal (from `backend\`)
```powershell
& $py scripts\run_batch.py --cases all --times 1 --mode demo     # replay the 6 recordings (smoke check, ~1.5 min)
& $py scripts\run_batch.py --cases 0131 --times 1                # one live run
& $py scripts\run_batch.py --cases 0142,0144 --times 3 --reset-before 0142   # several runs; wipe memory before 0142
& $py scripts\run_batch.py --cases all --times 3 --budget tight  # tight budget preset
& $py scripts\run_case.py 0142 --ci-only                         # check a case fails for the right reason
& $py scripts\run_case.py 0142 --reruns 10                       # rerun the failing test 10x
& $py scripts\run_case.py 0131 --ruff-fix                        # try the lint fix
```
Expected demo outcomes: 0142/0144/0128 `escalated`; 0139/0137/0131 `reported`.

## Recordings and scoreboard (from `backend\`)
```powershell
& $py scripts\export_demo_runs.py                  # best live run per case -> demo_runs\<id>.json
& $py scripts\export_demo_runs.py --case 0150      # one case (also works for live-added cases)
& $py scripts\export_variants.py                   # event fixtures for frontend tests
```
API (backend running):
```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/cases
Invoke-RestMethod http://127.0.0.1:8000/api/scoreboard
Invoke-RestMethod http://127.0.0.1:8000/api/runs/active
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/admin/reset-memory       # cold start
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/admin/export-demo-runs
```
In the UI: keys `1`-`6` pick a case, `Enter` runs, `S` scoreboard, `D` live/recorded, `T` budget, `E` export, `Esc` close.

## Add a case live (local, no GitHub)
From `backend\`:
```powershell
.\scripts\add_spare_case.ps1                                  # pre-staged case #0150 (fee sign bug)
& $py scripts\add_case.py new 0151 --slug x                   # branch, then break a file in backend\fixtures\ledger-core
& $py scripts\add_case.py finish 0151 --title "what failed" --cls regression
& $py scripts\add_case.py from-patch 0152 --slug y --patch some.diff --title "..." --cls lint
& $py scripts\add_case.py list
& $py scripts\add_case.py remove 0151                         # also remove 0150 after the demo
```
Then F5 in the UI, click the case, Run live. `--cls`: flaky, dependency, regression, lint, env.

## GitHub demo (real Actions + real draft PR)
Needs `backend\.env`: `GITHUB_TOKEN`, `GREENLINE_GITHUB_REPO=Pikathebot/ledger-core`, `GREENLINE_DRY_RUN=false`.
```powershell
.\demo_github.ps1 reset                # clear the last demo (case, PRs, branches)
.\demo_github.ps1 reset -ResetMemory   # same, plus a cold run (no memory recall)
.\demo_github.ps1 push                 # push the fee-sign bug; follows it to the draft PR
.\demo_github.ps1 push -Manual         # branch only: edit files in D:\ledger-dev, press Enter
.\demo_github.ps1 push -Cls lint       # set the class tag
```
The bug must be in a non-test file. Wait ~40 s for Actions to go red, then Greenline picks it up.
One-time repo setup (already done): `& $py scripts\setup_github_repo.py --create` from `backend\`.
Venue internet down: comment out `GREENLINE_GITHUB_REPO` in `.env`, restart, use the local live add.

## Checks
```powershell
cd backend; & $py -m pytest -q
cd frontend; npx vitest run; npm run build
```

## Git
```powershell
git switch feat/github-actions         # GitHub-demo work (B's laptop: git fetch origin first)
git switch main                        # stable demo state
git pull --rebase; git push            # sync
git tag                                # gate tags: cp1 g3 g4 pre-move
```
Never `git add -f` anything under `backend\models\`. Rules: `docs/14-GIT-WORKFLOW.md`.
