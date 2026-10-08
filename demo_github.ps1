# B18 demo helper: push a broken branch to the GitHub test repo and watch Greenline pick it up.
#
#   .\demo_github.ps1 reset                  clear the last demo (case, PR, branches); add -ResetMemory for a cold run
#   .\demo_github.ps1 push                   push the fee-sign bug (default patch) and follow the run to the PR
#   .\demo_github.ps1 push -Manual           branch only: edit files in D:\ledger-dev yourself, then press Enter
#   .\demo_github.ps1 push -Cls lint         set the ground-truth class tag (flaky|dependency|regression|lint|env)
#
# Needs: the stack running (start.bat), backend\.env with GITHUB_TOKEN / GREENLINE_GITHUB_REPO /
# GREENLINE_DRY_RUN=false, and `gh` logged in. The "developer" clone lives in D:\ledger-dev.
param(
    [Parameter(Mandatory = $true, Position = 0)][ValidateSet('reset', 'push')][string]$Action,
    [string]$Repo = 'Pikathebot/ledger-core',
    [string]$Clone = 'D:\ledger-dev',
    [string]$Branch = '',
    [string]$Message = 'payouts: add net_after_fee',
    [ValidateSet('flaky', 'dependency', 'regression', 'lint', 'env')][string]$Cls = 'regression',
    [string]$Patch = (Join-Path $PSScriptRoot 'backend\scripts\spare_cases\0150-fee-sign.diff'),
    [switch]$Manual,
    [switch]$ResetMemory,
    [string]$Api = 'http://127.0.0.1:8000'
)

$ErrorActionPreference = 'Stop'
$backend = Join-Path $PSScriptRoot 'backend'
$py = Join-Path $backend '.venv\Scripts\python.exe'

function Invoke-Git { & git -C $Clone @args; if ($LASTEXITCODE -ne 0) { throw "git $($args -join ' ') failed" } }

function Ensure-Clone {
    if (-not (Test-Path (Join-Path $Clone '.git'))) {
        Write-Host "[setup] cloning $Repo into $Clone"
        & git clone "https://github.com/$Repo.git" $Clone
        if ($LASTEXITCODE -ne 0) { throw 'clone failed' }
    }
    Invoke-Git fetch --prune origin
    Invoke-Git switch main
    Invoke-Git reset --hard origin/main
}

function Get-Cases { (Invoke-RestMethod "$Api/api/cases") | ForEach-Object { $_.id } }

if ($Action -eq 'reset') {
    Ensure-Clone

    # Greenline side: drop every GitHub-detected case (#7xxx).
    Push-Location $backend
    $listed = & $py scripts\add_case.py list
    foreach ($line in $listed) {
        if ($line -match '^#(7\d{3})\b') {
            Write-Host "[reset] removing case #$($Matches[1])"
            & $py scripts\add_case.py remove $Matches[1] | Out-Null
        }
    }
    Pop-Location

    # GitHub side: close open PRs, delete every branch except main.
    $prs = gh pr list --repo $Repo --state open --json number | ConvertFrom-Json
    foreach ($pr in $prs) {
        Write-Host "[reset] closing PR #$($pr.number)"
        gh pr close $pr.number --repo $Repo --delete-branch | Out-Null
    }
    Invoke-Git fetch --prune origin
    $remote = (& git -C $Clone branch -r --format='%(refname:short)') |
        Where-Object { $_ -like 'origin/*' -and $_ -ne 'origin/main' -and $_ -ne 'origin/HEAD' }
    foreach ($ref in $remote) {
        $name = $ref -replace '^origin/', ''
        Write-Host "[reset] deleting remote branch $name"
        Invoke-Git push origin --delete $name
    }
    foreach ($local in (& git -C $Clone branch --format='%(refname:short)' | Where-Object { $_ -ne 'main' })) {
        Invoke-Git branch -D $local | Out-Null
    }

    if ($ResetMemory) {
        Invoke-RestMethod -Method Post "$Api/api/admin/reset-memory" | Out-Null
        Write-Host '[reset] memory cleared (next run is cold)'
    }
    Write-Host '[reset] done. Refresh the UI: back to the six built-in cases.'
    return
}

# ---- push ----
try { $before = @(Get-Cases) } catch { throw "Greenline backend not reachable at $Api (run start.bat)" }

Ensure-Clone
if (-not $Branch) { $Branch = 'bug-' + (Get-Date -Format 'HHmmss') }
Invoke-Git switch -c $Branch

if ($Manual) {
    Write-Host "[push] branch $Branch created. Break a non-test file in $Clone so a test fails, then press Enter."
    Read-Host | Out-Null
} else {
    Invoke-Git apply --ignore-whitespace $Patch
}
Invoke-Git add -A
Invoke-Git commit -m "$Message [cls:$Cls]"
Invoke-Git push -u origin $Branch
$started = Get-Date
Write-Host "[push] pushed $Branch. GitHub Actions runs (about 30-40 s), then Greenline picks it up."
Write-Host "       Actions: https://github.com/$Repo/actions"

# Follow it: new case -> run -> draft PR.
$caseId = $null
for ($i = 0; $i -lt 60 -and -not $caseId; $i++) {
    Start-Sleep 4
    try {
        $caseId = Get-Cases | Where-Object { $_ -match '^7\d{3}$' -and $before -notcontains $_ } | Select-Object -First 1
    } catch { }
}
if (-not $caseId) {
    # A re-push of the same branch reuses its case; fall back to "the active run".
    $active = Invoke-RestMethod "$Api/api/runs/active"
    if ($active) { $caseId = $active.caseId }
}
if (-not $caseId) { Write-Host '[push] no case appeared after 4 minutes: check the Actions run and the backend log.'; return }
Write-Host "[push] Greenline registered case #$caseId. Watch it at http://localhost:5173"

$pr = $null
for ($i = 0; $i -lt 60 -and -not $pr; $i++) {
    Start-Sleep 4
    try {
        $raw = gh pr list --repo $Repo --state open --head "fix/$caseId" --json 'url,isDraft' 2>&1
        if ($LASTEXITCODE -ne 0) { throw ($raw | Select-Object -First 1) }
        $found = $raw | ConvertFrom-Json
        if ($found) { $pr = $found[0] }
    } catch { Write-Host "[push] (gh failed: $($_.Exception.Message.Split('.')[0]); retrying)" }
}
if ($pr) {
    Write-Host "[push] draft PR opened: $($pr.url)"
    Write-Host "       Actions on the PR should go green in about 40 s."
} else {
    Write-Host '[push] no PR yet (the run may have escalated; check the UI).'
}
