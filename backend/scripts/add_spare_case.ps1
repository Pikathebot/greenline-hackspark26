# Adds the pre-staged spare case #0150 (fee sign bug) to the running app. Press F5 in the UI after.
# Run from backend\:  .\scripts\add_spare_case.ps1
Set-Location $PSScriptRoot\..
& .\.venv\Scripts\python.exe scripts\add_case.py from-patch 0150 --slug fee-sign --patch scripts\spare_cases\0150-fee-sign.diff --title "test_net_after_fee_deducts_fee" --cls regression --beat "Added live: new case, real triage"
