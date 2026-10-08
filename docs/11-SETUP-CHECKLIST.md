# 11: Setup checklist (both laptops)

**Decision D15: tools and model weights are pre-staged before the event, on both laptops.**
The rule this kit follows: **pre-stage third-party, public artifacts only** (installers, model
weights, public Docker base images, public package downloads). **Nothing the team created** comes
along: no code, no built project images, no old databases, no old repo.

Still worth a quick confirmation from the organizers: (1) may we bring this documentation kit, and
(2) what's the judging format and slot length?

## 0. Pre-event staging (do this before 8 Oct, on BOTH laptops)

### What to stage, and what NOT to

| Stage it (third-party, public) | Do NOT carry over (team-created) |
|---|---|
| Tool installs (section 1) | This repo, or any of its code, `node_modules/`, `.venv/` |
| `Qwen3-8B-Q4_K_M.gguf`, `bge-small-en-v1.5-q8_0.gguf` | `greenline.db` (it holds old runs **and old memory traces**, which would fake the #0144 memory beat and pollute the scoreboard) |
| `docker pull python:3.12-slim` (public base image) | The `greenline-sandbox:latest` image (built from our old Dockerfile). **Rebuild it at the event.** |
| (optional) Phi-4-mini fallback GGUF | `backend/fixtures/ledger-core/`, `demo_runs/`, old `.env` |

### Steps

1. **Create the working folder at the same path on both laptops:** `D:\greenline\backend\models\`.
   `D:\greenline\` becomes the project repo at H+0:15. Until then it contains **only** the models.
   (If a laptop has no `D:` drive, use the same structure on another drive. The paths inside the
   project are all relative to `backend/`.)
2. **Move the models out of the old repo** on the laptop that has them:
   `D:\scripting\innovate-project\backend\models\` holds `Qwen3-8B-Q4_K_M.gguf` (5.03 GB) and
   `bge-small-en-v1.5-q8_0.gguf` (37 MB). Move both into `D:\greenline\backend\models\`.
3. **Copy them to the other laptop** (USB drive or LAN share), into the same folder. Nobody needs to
   re-download.
4. **Verify the copies** match on both machines (catches a truncated USB copy):
   `Get-FileHash D:\greenline\backend\models\*.gguf -Algorithm SHA256`, then compare the hashes
   between the laptops.
5. **Install the tools** (section 1) on both laptops, including the reboots for WSL2 and Docker.
6. **Pull the base image** on both: `docker pull python:3.12-slim`.
7. **Smoke-test the model runtime on both laptops.** This uses only the llama.cpp tool and no
   project code, so it's legitimate setup:
   - Start `llama-server` with the flags from `07-MODEL-RUNTIME.md`, pointing at `D:\greenline\backend\models\`.
   - Open `http://127.0.0.1:8080` (llama-server's built-in chat page), ask anything, and confirm
     the answer arrives within a few seconds and `nvidia-smi` shows about 7 GB used.
   - Run `llama-bench -m D:\greenline\backend\models\Qwen3-8B-Q4_K_M.gguf -ngl 99` and note the
     tokens/s.
   - **On the RTX 5070 laptop, try both the Vulkan (WinGet) and a CUDA (≥ 12.8) build. Keep the
     faster one**, so this decision is made before H+0.
8. **Claude Code:** install and log in on both laptops, each with its own account. Check which
   skills are available by typing `/`.
9. **Git:** do §1 of `14-GIT-WORKFLOW.md` on both laptops (identity, `gh auth login` over HTTPS,
    collaborator invite accepted).
9b. **Copy this kit** (`hackathon-kit/`) to both laptops **and** a USB drive, because it gets
   copied into the new repo as `docs/` at H+0:15.
10. **Charge both laptops** and pack the chargers, a USB drive, an HDMI cable/adapter, and a phone
    hotspot (in case the venue Wi-Fi blocks laptop-to-laptop traffic).

## 1. Tools (both laptops)

| Tool | Version | Install | Verify |
|---|---|---|---|
| Git | latest | `winget install Git.Git` | `git --version` |
| Node.js | 22 LTS | `winget install OpenJS.NodeJS.LTS` | `node -v` → v22.x |
| Python | 3.12 | `winget install Python.Python.3.12` (python.org build, so sqlite extension loading works) | `py -3.12 --version` |
| Docker Desktop | latest, **WSL2 backend** | `winget install Docker.DockerDesktop` (needs WSL2: `wsl --install` + reboot) | `docker info` shows `OSType: linux` |
| llama.cpp | recent | `winget install ggml.llamacpp` (Vulkan) **or** the GitHub release zip (CUDA build, CUDA ≥ 12.8 for the RTX 5070). Pick per laptop in §0 step 7. | `llama-server --version` |
| NVIDIA driver | latest Game Ready / Studio | GeForce Experience / nvidia.com | `nvidia-smi` |
| Claude Code | latest | Native installer or `npm install -g @anthropic-ai/claude-code`, then log in to **that person's own account** | `claude --version` |
| Editor | VS Code (optional) | `winget install Microsoft.VisualStudioCode` | (none) |
| Screen recorder | OBS Studio (or Xbox Game Bar) | `winget install OBSProject.OBSStudio` | Test a 10 s 1080p recording |

## 2. If something is missing at the venue

| Item | Size | Source |
|---|---|---|
| Qwen3-8B Q4_K_M GGUF | ~5.0 GB | Copy from the other laptop or the USB drive first. Last resort: Hugging Face `Qwen/Qwen3-8B-GGUF`. |
| bge-small-en-v1.5 q8_0 GGUF | ~37 MB | The same; last resort: a Hugging Face GGUF conversion of `BAAI/bge-small-en-v1.5` |
| `python:3.12-slim` | ~50 MB | `docker pull python:3.12-slim` |

## 3. Project dependencies (after the repo exists, H+0:15 onward)

Backend (`backend/`):
```
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install fastapi "uvicorn[standard]" pydantic pydantic-settings httpx docker langgraph sqlite-vec PyGithub pytest pytest-asyncio
docker build -t greenline-sandbox:latest greenline/sandbox
python scripts/seed_repo.py
```

Frontend (`frontend/`): scaffold with `npm create vite@latest frontend -- --template react-ts`,
then:
```
npm install zustand framer-motion @xyflow/react @fontsource-variable/inter @fontsource/jetbrains-mono
npm install -D tailwindcss @tailwindcss/vite vitest
```
(Swap the font packages for whatever the design locks: Geist, IBM Plex, etc.)

## 4. Verification (run at G0, and again before the demo)

```
nvidia-smi                                   # GPU visible, ~0 MB used before model start
docker info                                  # running, WSL2
docker run --rm --network none python:3.12-slim python -c "print('sandbox ok')"
.\scripts\llama-server.ps1                   # separate terminal; wait for "server is listening"
curl http://127.0.0.1:8080/health            # {"status":"ok"}
.\scripts\llama-embed.ps1                    # separate terminal
curl http://127.0.0.1:8081/health
uvicorn greenline.main:app --host 0.0.0.0 --port 8000   # separate terminal
curl http://127.0.0.1:8000/api/health        # every check reachable:true
```

Write these as `backend/scripts/check_env.ps1` (B2/B5), which prints a green/red line per check.

## 5. LAN between the laptops

- Same Wi-Fi or a phone hotspot. Find B's IP with `ipconfig` (IPv4 under the Wi-Fi adapter).
- On A: `VITE_API_TARGET=http://<B-ip>:8000` in `frontend/.env.local`, then restart Vite.
- If Windows Firewall blocks it: allow `python.exe` on **private** networks (prompted on the first
  uvicorn start with `--host 0.0.0.0`), and set the Wi-Fi profile to Private.
- If the venue Wi-Fi isolates clients, use a phone hotspot, or run the backend locally on A too
  (A's laptop has the same GPU class, so it is the spare anyway).

## 6. Demo-day machine prep (before each checkpoint; final: from 07:00)

- Plugged into power. Windows power mode set to **Best performance**. Laptop vendor tool on
  performance/turbo.
- Windows Update paused. Notifications off (Focus / Do Not Disturb). Auto-sleep off. Screen saver
  off.
- Close Chrome (HW acceleration uses VRAM), Discord, games and anything else using the GPU.
- Display: 1920×1080, scaling 100% or 125% (whichever was rehearsed). Test the HDMI to the
  projector if possible.
- Browser: one window, full screen (F11), zoom at 100%, bookmarks bar hidden, extensions off
  (use a fresh browser profile).

## 7. Venue move at 16:15 (D17)

Everything must survive a bag and a new network.

- **15:45:** push + tag `pre-move` (`14-GIT-WORKFLOW.md` §5). Stop uvicorn, Vite, both `llama-server`s.
  Quit Docker Desktop (or at least `docker ps -a` empty). Shut the lid only after Claude Code
  sessions are idle: a sleeping laptop kills in-flight work.
- Pack: both chargers + extension strip, HDMI cable/adapter, USB drive (models + kit + backup
  video), phone hotspot ready.
- **At the new venue:** power first (the GPU model drains a battery fast), then Wi-Fi or hotspot,
  Docker Desktop (wait for the whale to stop animating), `llama-server.ps1`, `llama-embed.ps1`,
  uvicorn, `check_env.ps1`. **B's LAN IP will have changed**: `ipconfig`, then A edits
  `frontend/.env.local` and restarts Vite. Re-check the firewall prompt (set the network Private).
- Budget 45 min. If it is over 60, A runs the whole stack locally (the 4060 laptop is the spare).
