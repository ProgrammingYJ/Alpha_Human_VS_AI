$ErrorActionPreference = 'Stop'
$taskRoot = 'C:\Users\Administrator\Desktop\Alpha-Captcha-AI'
$entryPath = Join-Path $taskRoot 'scripts\start_remote_engine.ps1'
$runnerPath = Join-Path $taskRoot 'scripts\run_remote_engine.py'
$all = @(Get-CimInstance Win32_Process)
$oldConsole = $all | Where-Object { $_.ProcessId -eq 6916 }
$oldVenv = $all | Where-Object { $_.ProcessId -eq 49352 }
$oldBase = $all | Where-Object { $_.ProcessId -eq 16984 }
$stopped = @()
if ($oldConsole -or $oldVenv -or $oldBase) {
    if (-not ($oldConsole.Name -eq 'powershell.exe' -and $oldConsole.CommandLine.Contains($entryPath) -and
        $oldVenv.Name -eq 'python.exe' -and $oldVenv.ParentProcessId -eq $oldConsole.ProcessId -and $oldVenv.CommandLine.Contains($runnerPath) -and
        $oldBase.Name -eq 'python.exe' -and $oldBase.ParentProcessId -eq $oldVenv.ProcessId -and $oldBase.CommandLine.Contains($runnerPath))) {
        throw 'Engine identity changed; nothing stopped.'
    }
    foreach ($enginePid in @(16984,49352,6916)) {
        Stop-Process -Id $enginePid -ErrorAction SilentlyContinue
        $stopped += $enginePid
    }
}
$otherEngines = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine.Contains($runnerPath) })
if ($otherEngines.Count -ne 0) { throw 'Another engine exists; no duplicate launched.' }
# Visible operator console is needed for hidden interactive A/B code entry.
$console = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$entryPath+'"')) -WorkingDirectory $taskRoot -PassThru
$record = @{checked_at_utc=(Get-Date).ToUniversalTime().ToString('o');console_pid=$console.Id;old_verified_chain_stopped=$stopped;
    minimum_tile_interval_seconds=0.25;selection_plan_preferred=$true;codes_entered_by_agent=0;startup_verified=$false;kept_running=$true}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskRoot 'runs\site-publish\scheduled-current-engine.json') -Encoding utf8
$record | ConvertTo-Json -Depth 5
