$ErrorActionPreference = 'Stop'
$taskRoot = 'C:\Users\Administrator\Desktop\Alpha-Captcha-AI'
$entryPath = Join-Path $taskRoot 'scripts\start_remote_engine.ps1'
$allProcesses = @(Get-CimInstance Win32_Process)
$oldRoot = $allProcesses | Where-Object { $_.ProcessId -eq 44388 }
$oldVenv = $allProcesses | Where-Object { $_.ProcessId -eq 39712 }
$oldBase = $allProcesses | Where-Object { $_.ProcessId -eq 39120 }
$stopped = @()
if ($oldRoot -or $oldVenv -or $oldBase) {
    if (-not ($oldRoot.Name -eq 'powershell.exe' -and $oldRoot.CommandLine.Contains($entryPath) -and
        $oldVenv.Name -eq 'python.exe' -and $oldVenv.ParentProcessId -eq $oldRoot.ProcessId -and
        $oldVenv.CommandLine.Contains((Join-Path $taskRoot 'scripts\run_remote_engine.py')) -and
        $oldBase.Name -eq 'python.exe' -and $oldBase.ParentProcessId -eq $oldVenv.ProcessId -and
        $oldBase.CommandLine.Contains((Join-Path $taskRoot 'scripts\run_remote_engine.py')))) {
        throw 'Known engine identity changed; no process stopped.'
    }
    foreach ($enginePid in @(39120,39712,44388)) {
        Stop-Process -Id $enginePid -Force -ErrorAction SilentlyContinue
        $stopped += $enginePid
    }
}
$otherEngines = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and $_.CommandLine -match 'run_remote_engine\.py'
})
if ($otherEngines.Count -ne 0) { throw 'Another remote engine is already running; no duplicate started.' }
# The operator uses this interactive console to enter A/B pair codes.
$newConsole = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$entryPath+'"')) -WorkingDirectory $taskRoot -PassThru
$record = @{checked_at_utc=(Get-Date).ToUniversalTime().ToString('o'); old_verified_chain_stopped=$stopped;
    console_pid=$newConsole.Id; engine_source_protocol=2; minimum_tile_interval_seconds=0.25;
    codes_entered_by_agent=0; kept_running=$true; startup_verified=$false}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskRoot 'runs\site-publish\quarter-current-engine.json') -Encoding utf8
$record | ConvertTo-Json -Depth 5
