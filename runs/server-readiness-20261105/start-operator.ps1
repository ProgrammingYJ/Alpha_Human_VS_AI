$ErrorActionPreference = 'Stop'
$taskRoot = 'C:\Users\Administrator\Desktop\Alpha-Captcha-AI'
$entryPath = Join-Path $taskRoot 'scripts\start_remote_engine.ps1'
$runnerPath = Join-Path $taskRoot 'scripts\run_remote_engine.py'
$reportPath = Join-Path $taskRoot 'runs\server-readiness-20261105\operator-start.json'
if (Test-Path -LiteralPath $reportPath) { throw 'Preserve the previous operator start record.' }
if (-not (Test-Path -LiteralPath $entryPath -PathType Leaf)) { throw 'The regular operator launcher is missing.' }
$engines = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and $_.CommandLine -and $_.CommandLine.Contains($runnerPath)
})
if ($engines.Count -ne 0) { throw 'An operator engine already exists; no duplicate launched.' }
# This visible console is required for the user's hidden A/B pairing input.
$console = Start-Process -FilePath 'powershell.exe' -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $entryPath + '"')
) -WorkingDirectory $taskRoot -PassThru
$record = @{
    checked_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    console_pid = $console.Id
    launcher = 'scripts/start_remote_engine.ps1'
    old_engine_count = 0
    processes_stopped = @()
    codes_entered_by_agent = 0
    interactive_console = $true
    startup_verified = $false
    kept_running = $true
}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding utf8
$record | ConvertTo-Json -Depth 5
