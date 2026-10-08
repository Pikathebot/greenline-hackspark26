# Starts the whole Greenline stack locally: llama-server, embeddings, API, UI.
# Usage: .\start.ps1   (or double-click start.bat)
# Each service gets its own window so you can see its logs. Stop with .\stop.ps1.
$ErrorActionPreference = 'Continue'
$root = $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'

function Test-Port($port) {
    [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

function Start-Service($name, $port, $dir, $cmd) {
    if (Test-Port $port) { Write-Host "[skip] $name already listening on :$port"; return }
    Write-Host "[start] $name (:$port)"
    Start-Process powershell -WorkingDirectory $dir -ArgumentList '-NoExit', '-Command', "`$host.UI.RawUI.WindowTitle='greenline: $name'; $cmd"
}

function Wait-Http($name, $url, $timeoutSec) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 3 | Out-Null
            Write-Host "[ok]    $name ready"
            return
        } catch { Start-Sleep 2 }
    }
    Write-Host "[WARN]  $name not ready after ${timeoutSec}s, check its window"
}

# Docker is needed for the sandbox
docker info --format '{{.OSType}}' *> $null
if ($LASTEXITCODE -ne 0) { Write-Host '[WARN]  Docker is not running. Start Docker Desktop (sandbox runs will fail).' }

Start-Service 'llama-server' 8080 $backend '.\scripts\llama-server.ps1'
Start-Service 'llama-embed'  8081 $backend '.\scripts\llama-embed.ps1'
Start-Service 'api'          8000 $backend '.venv\Scripts\activate; uvicorn greenline.main:app --host 0.0.0.0 --port 8000'
Start-Service 'ui'           5173 $frontend 'npm run dev'

Wait-Http 'llama-server' 'http://127.0.0.1:8080/health' 120
Wait-Http 'llama-embed'  'http://127.0.0.1:8081/health' 60
Wait-Http 'api'          'http://127.0.0.1:8000/api/health' 60
Wait-Http 'ui'           'http://localhost:5173' 60

Write-Host ''
& (Join-Path $backend 'scripts\check_env.ps1')
Write-Host ''
Write-Host 'UI: http://localhost:5173'
Start-Process 'http://localhost:5173'
