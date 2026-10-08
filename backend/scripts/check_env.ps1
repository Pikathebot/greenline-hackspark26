# B0 / B5: prints one green/red line per check from docs/11-SETUP-CHECKLIST.md §4.
# Run from anywhere. Does not start any servers; it only checks what's already running.

$ErrorActionPreference = "Continue"
$backendRoot = Split-Path -Parent $PSScriptRoot

function Report($label, $ok, $detail = "") {
    $mark = if ($ok) { "[OK]  " } else { "[FAIL]" }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host "$mark $label $detail" -ForegroundColor $color
    return $ok
}

$allOk = $true

# 1. nvidia-smi
try {
    $gpu = nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>$null
    $allOk = (Report "nvidia-smi" $true $gpu) -and $allOk
} catch {
    $allOk = (Report "nvidia-smi" $false "not found") -and $allOk
}

# 2. docker info
try {
    $dockerOs = docker info --format '{{.OSType}}' 2>$null
    $ok = ($dockerOs -eq "linux")
    $allOk = (Report "docker info" $ok "OSType=$dockerOs") -and $allOk
} catch {
    $allOk = (Report "docker info" $false "daemon unreachable") -and $allOk
}

# 3. sandbox network isolation smoke test
try {
    $out = docker run --rm --network none python:3.12-slim python -c "print('sandbox ok')" 2>$null
    $ok = ($out -match "sandbox ok")
    $allOk = (Report "sandbox smoke (--network none)" $ok $out) -and $allOk
} catch {
    $allOk = (Report "sandbox smoke (--network none)" $false "docker run failed") -and $allOk
}

# 4. models present
$modelsDir = if ($env:GREENLINE_MODELS_DIR) { $env:GREENLINE_MODELS_DIR } else { Join-Path $backendRoot "models" }
$genModel = Join-Path $modelsDir "Qwen3-8B-Q4_K_M.gguf"
$embedModel = Join-Path $modelsDir "bge-small-en-v1.5-q8_0.gguf"
$allOk = (Report "generation model present" (Test-Path $genModel) $genModel) -and $allOk
$allOk = (Report "embedding model present" (Test-Path $embedModel) $embedModel) -and $allOk

# 5. llama-server generation :8080/health
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8080/health" -TimeoutSec 2 -ErrorAction Stop
    $allOk = (Report "llama-server :8080/health" $true ($resp | ConvertTo-Json -Compress)) -and $allOk
} catch {
    $allOk = (Report "llama-server :8080/health" $false "not reachable (start scripts\llama-server.ps1)") -and $allOk
}

# 6. llama-server embedding :8081/health
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8081/health" -TimeoutSec 2 -ErrorAction Stop
    $allOk = (Report "llama-embed :8081/health" $true ($resp | ConvertTo-Json -Compress)) -and $allOk
} catch {
    $allOk = (Report "llama-embed :8081/health" $false "not reachable (start scripts\llama-embed.ps1)") -and $allOk
}

# 7. backend :8000/api/health
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
    $allOk = (Report "backend :8000/api/health" $true ($resp | ConvertTo-Json -Compress -Depth 5)) -and $allOk
} catch {
    $allOk = (Report "backend :8000/api/health" $false "not reachable (start uvicorn)") -and $allOk
}

Write-Host ""
if ($allOk) {
    Write-Host "All checks passed." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some checks failed (see [FAIL] lines above)." -ForegroundColor Yellow
    exit 1
}
