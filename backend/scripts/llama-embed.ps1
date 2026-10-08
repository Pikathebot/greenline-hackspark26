# B0: starts the embedding llama-server (bge-small, CPU-only so it never competes for VRAM).
# Override the exe with $env:LLAMA_SERVER, the models folder with $env:GREENLINE_MODELS_DIR.

$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
$modelsDir = if ($env:GREENLINE_MODELS_DIR) { $env:GREENLINE_MODELS_DIR } else { Join-Path $backendRoot "models" }
$modelPath = Join-Path $modelsDir "bge-small-en-v1.5-q8_0.gguf"

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
    --embedding `
    -ngl 0 `
    --host 127.0.0.1 `
    --port 8081
