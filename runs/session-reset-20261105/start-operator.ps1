$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$entryPath = Join-Path $taskRoot 'scripts\start_remote_engine.ps1'
$runnerPath = Join-Path $taskRoot 'scripts\run_remote_engine.py'
$reportPath = Join-Path $PSScriptRoot 'operator-start.json'
if (Test-Path -LiteralPath $reportPath) { throw 'Preserve previous operator start record.' }
if (-not (Test-Path -LiteralPath $entryPath -PathType Leaf)) { throw 'Missing regular operator launcher.' }
$engines = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and $_.CommandLine -and $_.CommandLine.Contains($runnerPath)
})
if ($engines.Count -ne 0) { throw 'Operator already exists; no duplicate launched.' }
# The visible console is for the user's interactive hidden A/B pairing input.
$console = Start-Process -FilePath 'powershell.exe' -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $entryPath + '"'),
    '-InferenceMode', 'parallel'
) -WorkingDirectory $taskRoot -PassThru
$record = [ordered]@{
    checked_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    console_pid = $console.Id
    launcher = 'scripts/start_remote_engine.ps1'
    inference_mode_requested = 'parallel'
    old_engine_count = 0
    interactive_console = $true
    startup_verified = $false
    agent_codes_entered = 0
    room_tokens_persisted = $false
    kept_running = $true
}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding utf8
$record | ConvertTo-Json -Depth 5
