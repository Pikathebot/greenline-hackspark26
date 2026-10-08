# B0: starts the generation llama-server (Qwen3-8B, GPU, thinking disabled).
# Run from anywhere; paths below are resolved relative to backend/.
# Override the exe with $env:LLAMA_SERVER, the models folder with $env:GREENLINE_MODELS_DIR.

$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
$modelsDir = if ($env:GREENLINE_MODELS_DIR) { $env:GREENLINE_MODELS_DIR } else { Join-Path $backendRoot "models" }
$modelPath = Join-Path $modelsDir "Qwen3-8B-Q4_K_M.gguf"

if (-not (Test-Path $modelPath)) {
    Write-Error "Model not found: $modelPath. Pre-stage it in backend\models\ before starting."
    exit 1
}

function Resolve-LlamaServer {
    if ($env:LLAMA_SERVER -and (Test-Path $env:LLAMA_SERVER)) {
        return $env:LLAMA_SERVER
    }
    $onPath = Get-Command llama-server -ErrorAction SilentlyContinue
    if ($onPath) {
        return $onPath.Source
    }
    $wingetDefault = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe\llama-server.exe"
    if (Test-Path $wingetDefault) {
        return $wingetDefault
    }
    Write-Error "llama-server.exe not found. Set `$env:LLAMA_SERVER to its full path, or 'winget install ggml.llamacpp'."
    exit 1
}

$exe = Resolve-LlamaServer
Write-Output "Using llama-server: $exe"
Write-Output "Model: $modelPath"

& $exe `
    -m $modelPath `
    -ngl 99 `
    -c 16384 `
    --cache-type-k q8_0 `
    --cache-type-v q8_0 `
    --flash-attn on `
    --jinja `
    --reasoning-budget 0 `
    --host 127.0.0.1 `
    --port 8080
