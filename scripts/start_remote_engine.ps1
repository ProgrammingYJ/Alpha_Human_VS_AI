[CmdletBinding()]
param(
    [ValidateSet('cuda', 'cpu')][string]$Device = 'cuda',
    [ValidateRange(30, 86400)][int]$WaitSeconds = 1800,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw '프로젝트 .venv Python이 없습니다. docs/SETUP.md를 확인하세요.'
}
$runId = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
$outputPath = Join-Path $projectRoot ('runs\remote-engine\' + $runId)
$runnerArguments = @((Join-Path $PSScriptRoot 'run_remote_engine.py'),
    '--base-url', 'https://bot.marulee.dev', '--device', $Device,
    '--wait-seconds', "$WaitSeconds", '--output', $outputPath)
if (-not $DryRun) { $runnerArguments += '--execute' }
Write-Host '인간 화면과 AI 표시 화면을 연결하는 A/B 원격 PC 엔진입니다. OS 마우스를 사용하지 않습니다.'
Write-Host '최초에만 각 인간 화면에서 Remote A/B 방을 만들고, 별도 AI 표시 화면을 연결하세요.'
Write-Host '모델 로드 후 최초 한 번 A CODE8 또는 B CODE8을 입력합니다. 다음 참가자는 같은 방의 다음 참가자 준비를 누릅니다.'
Write-Host 'PC 엔진과 AI 표시 화면은 연결을 유지합니다. 연결을 바꿀 때만 stop A/B를 사용하며 진행 중 해당 봇은 중단됩니다.'
Write-Host ('실행 기록: ' + $outputPath)
Push-Location -LiteralPath $projectRoot
try {
    & $pythonPath @runnerArguments
    exit $LASTEXITCODE
}
finally { Pop-Location }
