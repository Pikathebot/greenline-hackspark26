# 07: Local model runtime

## Models

| Role | Model | File | Size | Where it runs |
|---|---|---|---|---|
| Generation | **Qwen3-8B, Q4_K_M GGUF** | `Qwen3-8B-Q4_K_M.gguf` | ~5.0 GB | GPU, all layers |
| Embeddings | **bge-small-en-v1.5, q8_0 GGUF** | `bge-small-en-v1.5-q8_0.gguf` | ~37 MB | CPU only |
| Fallback (generation) | Phi-4-mini (3.8B) GGUF Q4_K_M | (varies) | ~2.5 GB | GPU. Only if Qwen3-8B is too slow or unstable. Weaker reasoning. |

**Sources** (verify the exact file names at download time):
- Qwen3-8B GGUF: the official Qwen repo on Hugging Face, `Qwen/Qwen3-8B-GGUF`.
- bge-small GGUF: a community GGUF conversion of `BAAI/bge-small-en-v1.5` on Hugging Face (search
  "bge-small-en-v1.5 gguf", and pick a q8_0 file around 37 MB with 384-dim output).

**Already downloaded.** Both files are pre-staged in `D:\greenline\backend\models\` on **both**
laptops before the event (D15). That folder is **gitignored from the first commit**, because GitHub
rejects files over 100 MB, so one accidental commit would break every push.

## Why this model (decided; don't re-litigate)

- Both laptops have **8 GB VRAM** (RTX 4060 laptop, RTX 5070 laptop).
- Qwen3-8B Q4_K_M ≈ 5.0 GB weights + about 2 GB KV cache at 16k context with q8_0 KV ≈ **7.0 GB**.
  On the 4060 it measured 7178 MiB of 8188 MiB, so it fits fully resident with headroom.
- Qwen3.5-9B (~6.6 GB) leaves too little room for KV, and overflow spills to system RAM, which is
  slow. Phi-4-mini is roomy but too weak for the Analyst and Patcher.
- Measured on the RTX 4060 laptop (Vulkan build, thinking off): about **1.4 s per structured call**
  on average. 20/20 schema round-trips succeeded.

## `llama-server` install

Either works on Windows:
- **WinGet:** `winget install ggml.llamacpp`. This shipped a **Vulkan** build last time, which works
  on any NVIDIA GPU.
- **GitHub release zip** from `ggml-org/llama.cpp` releases: choose a **CUDA** Windows build for
  more throughput. The RTX 5070 (Blackwell) needs a build compiled against **CUDA 12.8 or newer**.
  If the CUDA build won't start or is slower, use the Vulkan build. Measure both (before the event, or 11:00–12:00 at the latest) and
  keep the faster one.

Check the GPU is used: the server log should report all layers offloaded (`offloaded 37/37 layers`
or similar), and `nvidia-smi` should show about 7 GB in use.

## Launch flags: generation (`scripts/llama-server.ps1`)

| Flag | Value | Why |
|---|---|---|
| `-m` | `models\Qwen3-8B-Q4_K_M.gguf` (relative to `backend/`) | Pre-staged, gitignored |
| `-ngl` | `99` | All layers on GPU |
| `-c` | `16384` | Context. Prompts carry CI logs, test files and diffs. |
| `--cache-type-k` / `--cache-type-v` | `q8_0` / `q8_0` | Halves the KV footprint with negligible quality cost |
| `--flash-attn` | `on` | **Must have an explicit value.** A bare `-fa` swallows the next flag. |
| `--jinja` | (none) | **Required**: model chat template, needed for reliable `json_schema` output |
| `--reasoning-budget` | `0` | **Disable Qwen3 thinking.** With it on, one call took minutes. |
| `--host` / `--port` | `127.0.0.1` / `8080` | Only the backend talks to it |

The script should check the model file exists and print a clear error if not.

## Launch flags: embeddings (`scripts/llama-embed.ps1`)

`-m models\bge-small-en-v1.5-q8_0.gguf --embedding -ngl 0 --host 127.0.0.1 --port 8081`.
`-ngl 0` keeps it **CPU-only** so it never competes with generation for VRAM.

API: `POST /v1/embeddings {"input": "<text>"}` → `data[0].embedding` (384 floats). L2-normalise
it before storing or querying.

## Structured output

Every call sends `response_format: {type: "json_schema", json_schema: {name, schema, strict: true}}`
to `/v1/chat/completions`. llama-server compiles the schema into a grammar, so the model *cannot*
emit non-JSON. Keep schemas **flat** (no nested models / `$ref`). Literals and enums are fine.

Smoke test (first thing after the server starts): send `TriageOutput` for the 0139 CI log 20
times. It must parse 20/20, at an average under 3 s.

## Temperatures

| Node | Temp |
|---|---|
| triage, analyst, reporter | 0.3 |
| patcher | 0.1 |
| critic | 0.4 (sample diversity for self-consistency) |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| A call takes minutes | Thinking mode on | `--reasoning-budget 0` |
| `unknown value for --flash-attn: '--jinja'` | Bare `-fa` | `--flash-attn on` |
| Prose instead of JSON | No `--jinja`, or `response_format` not sent | Add `--jinja`; check the payload |
| 500 on schema | Nested `$ref` | Flatten the Pydantic models |
| GPU util ~0%, slow | Layers not offloaded / wrong build | Check the startup log; try the other build (CUDA ↔ Vulkan) |
| VRAM > 7.5 GB, stutter | Unquantised KV or larger context | Confirm `q8_0` KV and `-c 16384`; close other GPU apps (browsers with HW accel, games) |
| Slower over time on stage | Thermal throttling / on battery | **Plug in power**, Windows "Best performance" power mode, laptop vendor performance profile |
| Embedding server steals VRAM | `-ngl` > 0 | `-ngl 0` |
