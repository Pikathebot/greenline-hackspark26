# B15: spare laptop runbook (the RTX 4060 laptop)

Goal: the whole stack runs on this laptop, so if the 5070 laptop (B's) dies or the venue Wi-Fi isolates
clients, the demo still works. Done = step 7 passes. Based on `11-SETUP-CHECKLIST.md` §3-§4.

Run everything from PowerShell. Nothing here needs a `.env`: the defaults match B's laptop.

## 1. Code
```
git pull
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 2. Models (copy from the USB drive; they are gitignored, never commit or `git add -f` them)
Put both files in `backend\models\`:
- `Qwen3-8B-Q4_K_M.gguf`
- `bge-small-en-v1.5-q8_0.gguf`

`llama-server.exe` must be on PATH or in the winget location; otherwise set `$env:LLAMA_SERVER`.

## 3. Sandbox image and fixture repo (Docker Desktop must be running, WSL2)
```
docker build -t greenline-sandbox:latest greenline/sandbox
python scripts/seed_repo.py
```
The seed creates `backend\fixtures\ledger-core` (gitignored). Rebuild the image at the venue; the
checklist says the old one can't be trusted.

## 4. Start the stack (three terminals, each from `backend\`)
```
.\scripts\llama-server.ps1       # wait for "server is listening" (8080)
.\scripts\llama-embed.ps1        # 8081
.venv\Scripts\activate; uvicorn greenline.main:app --host 0.0.0.0 --port 8000
```
Allow `python.exe` on **private** networks if Windows asks.

## 5. Check
```
.\scripts\check_env.ps1
```
Every line must be `[OK]`.

## 6. Frontend
`frontend\.env.local`:
```
VITE_API_TARGET=http://127.0.0.1:8000
```
Then `npm ci` (first time) and `npm run dev`; open http://localhost:5173.

## 7. Acceptance
```
.venv\Scripts\python.exe scripts\run_batch.py --cases all --times 1 --mode demo
.venv\Scripts\python.exe scripts\run_batch.py --cases 0131 --times 1
```
- The first line must print six outcomes: 0142/0144/0128 `escalated`, 0139/0137/0131 `reported`. Each
  recording replays at its recorded pace (about 1.5 minutes in total).
- The second is one live #0131: it must end `reported`. It proves the model and sandbox work here.
- Optional: in the browser, start #0144 with Recorded on and check that the memory callout and the
  skipped Reproducer show.

## Notes
- The database starts empty here, so the scoreboard is empty until you run a live batch. The deck numbers
  come from B's laptop (`/api/scoreboard` there). Don't quote numbers from this laptop unless you ran a
  batch of your own.
- Live #0144 only skips reproduction when memory holds a #0142 trace: run a live #0142 first. Reset with
  `POST /api/admin/reset-memory`.
- Keep the 4060 free for model work during the demo: close Chrome with hardware acceleration, games and
  Discord.
