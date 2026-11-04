$ErrorActionPreference = 'Stop'
$taskRoot = 'C:\Users\Administrator\Desktop\Alpha-Captcha-AI'
$entryPath = Join-Path $taskRoot 'scripts\start_remote_engine.ps1'
$runnerPath = Join-Path $taskRoot 'scripts\run_remote_engine.py'
$existing = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and $_.CommandLine -and $_.CommandLine.Contains($runnerPath)
})
if ($existing.Count -ne 0) { throw 'An operator engine already exists; no duplicate was launched.' }
# This visible console is the user-authorized interactive lane/code prompt.
$console = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$entryPath+'"')) -WorkingDirectory $taskRoot -PassThru
$record = @{
    checked_at_utc=(Get-Date).ToUniversalTime().ToString('o'); console_pid=$console.Id;
    old_engine_count=0; old_engine_processes_stopped=@(); codes_entered_by_agent=0;
    image_readiness_barrier_supported=$true; minimum_tile_interval_seconds=0.25;
    startup_verified=$false; kept_running=$true
}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskRoot 'runs\site-publish\reliability-current-engine.json') -Encoding utf8
$record | ConvertTo-Json -Depth 5
