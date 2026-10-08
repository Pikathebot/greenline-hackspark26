# Stops the Greenline services started by start.ps1 (kills whatever listens on their ports).
foreach ($p in 8080, 8081, 8000, 5173) {
    Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object {
            Write-Host "[stop] :$p (pid $($_.OwningProcess))"
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
}
