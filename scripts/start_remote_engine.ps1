[CmdletBinding()]
param(
    [ValidateSet('cuda', 'cpu')][string]$Device = 'cuda',
    [ValidateSet('single', 'parallel', 'serial')][string]$InferenceMode = 'single',
    [ValidateScript({ -not [double]::IsNaN($_) -and -not [double]::IsInfinity($_) -and $_ -gt 0 -and $_ -le 1 })][double]$GpuDutyCycle = 0.30,
    [ValidateRange(1, 64)][int]$CpuThreads = 4,
    [ValidateRange(30, 86400)][int]$WaitSeconds = 1800,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw '프로젝트 .venv Python이 없습니다. docs/SETUP.md를 확인하세요.'
}
$runId = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
$outputPath = Join-Path $projectRoot ('runs\remote-engine\' + $runId)
$runnerArguments = @((Join-Path $PSScriptRoot 'run_remote_engine.py'),
    '--base-url', 'https://bot.marulee.dev', '--device', $Device,
    '--inference-mode', $InferenceMode,
    '--gpu-duty-cycle', $GpuDutyCycle.ToString('R', [Globalization.CultureInfo]::InvariantCulture),
    '--cpu-threads', "$CpuThreads",
    '--wait-seconds', "$WaitSeconds", '--output', $outputPath)
if (-not $DryRun) { $runnerArguments += '--execute' }
$env:OMP_NUM_THREADS = "$CpuThreads"
$env:MKL_NUM_THREADS = "$CpuThreads"
Write-Host '인간 화면과 AI 표시 화면을 연결하는 원격 PC 엔진입니다. OS 마우스를 사용하지 않습니다.'
if ($InferenceMode -eq 'single') {
    Write-Host 'A 단일 구역 운영: 인간 화면에서 방을 만들고 AI 표시 화면을 연결하세요. B 연결은 사용하지 않습니다.'
    Write-Host '모델 로드 후 최초 한 번 새8자리코드만 입력합니다(A CODE8도 가능). 다음 참가자는 같은 방의 다음 참가자 준비를 누릅니다.'
} else {
    Write-Host ('추론 모드: ' + $InferenceMode + ' (parallel은 A/B 독립 슬롯 2개, serial은 FIFO 슬롯 1개입니다.)')
    Write-Host '최초에 각 인간/AI 표시 화면을 연결하고 모델 로드 후 A CODE8 또는 B CODE8을 입력합니다.'
}
Write-Host ('GPU 협력적 실행시간 예산: ' + ($GpuDutyCycle * 100).ToString('0.##') + '% (순간 GPU 사용률/SM/VRAM 고정 할당이 아닙니다.)')
Write-Host ('이 PC 봇의 CPU 스레드: ' + $CpuThreads + '. Python 프로세스는 BelowNormal 우선순위를 요청합니다.')
Write-Host 'PC 엔진과 AI 표시 화면은 연결을 유지합니다. 연결을 바꿀 때만 stop을 사용하며 진행 중 해당 봇은 중단됩니다.'
Write-Host ('실행 기록: ' + $outputPath)
Push-Location -LiteralPath $projectRoot
try {
    & $pythonPath @runnerArguments
    exit $LASTEXITCODE
}
finally { Pop-Location }
