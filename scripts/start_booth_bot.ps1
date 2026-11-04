[CmdletBinding()]
param(
    [string]$RoomCode,
    [string]$Config = 'configs/booth-bot.local.json',
    [ValidateSet('cuda', 'cpu')][string]$Device = 'cuda',
    [ValidateRange(30, 86400)][int]$WaitSeconds = 900,
    [switch]$Calibrate,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runnerPath = Join-Path $PSScriptRoot 'run_booth_bot.py'
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw '프로젝트 .venv Python이 없습니다. docs/SETUP.md의 PC 설치 절차를 확인하세요.'
}
if (-not [IO.Path]::IsPathRooted($Config)) { $Config = Join-Path $projectRoot $Config }
$Config = [IO.Path]::GetFullPath($Config)
$needsCalibration = $Calibrate.IsPresent -or -not (Test-Path -LiteralPath $Config -PathType Leaf)
if (-not $needsCalibration) {
    $layout = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
    $needsCalibration = $layout.calibrated -isnot [bool] -or $layout.calibrated -ne $true
}

Push-Location -LiteralPath $projectRoot
try {
    if ($needsCalibration) {
        $calibratorPath = Join-Path $PSScriptRoot 'calibrate_booth_bot.py'
        if (-not (Test-Path -LiteralPath $calibratorPath -PathType Leaf)) {
            throw '실측한 보정 설정이 필요합니다. scripts/calibrate_booth_bot.py를 먼저 준비하세요.'
        }
        Write-Host '먼저 봇 창과 화면 좌표를 직접 보정합니다. 예시 좌표는 실제 클릭에 사용하지 않습니다.'
        $calibratorArguments = @($calibratorPath, '--output', $Config)
        if (Test-Path -LiteralPath $Config -PathType Leaf) {
            if (-not $Calibrate) {
                throw '기존 설정이 미보정 상태입니다. Start-Alpha-Bot.cmd -Calibrate로 직접 보정하세요. 기존 파일을 자동 교체하지 않습니다.'
            }
            $calibratorArguments += '--replace'
        }
        & $pythonPath @calibratorArguments
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    $layout = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($layout.calibrated -isnot [bool] -or $layout.calibrated -ne $true) {
        throw 'calibrated=true인 실측 설정이 필요합니다. 예시 설정을 임의로 바꾸지 마세요.'
    }
    if ([string]::IsNullOrWhiteSpace($RoomCode)) {
        $RoomCode = Read-Host '인간 화면에서 새 대결방을 만들고 8자리 연결 코드를 입력하세요'
    }
    $RoomCode = $RoomCode.Trim().ToUpperInvariant()
    if ($RoomCode -cnotmatch '^[A-Z2-9]{8}$') { throw '연결 코드는 영문 대문자와 숫자 2~9의 8자리입니다.' }
    $runId = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
    $outputPath = Join-Path $projectRoot ('runs\booth-live\' + $runId)
    $runnerArguments = @($runnerPath, '--config', $Config, '--room', $RoomCode,
        '--base-url', 'https://bot.marulee.dev', '--open-browser', '--rounds', '1',
        '--tree-model', 'grounding-dino', '--device', $Device, '--timeout-seconds', "$WaitSeconds",
        '--render-wait-seconds', '1.0', '--output', $outputPath)
    if (-not $DryRun) { $runnerArguments += @('--execute', '--ready') }
    Write-Host '웹 봇 화면에서 먼저 참가하면 안 됩니다. 이 실행기가 직접 참가하고 모델·화면 확인 후 준비를 알립니다.'
    Write-Host '봇 창을 전면에 유지하세요. 인간 화면은 패드에서 시작하거나 같은 PC라면 시작 후 봇 창으로 돌아오세요.'
    Write-Host ('이번 한 판의 기록: ' + $outputPath)
    Write-Host '한 판이 끝나면 실행기가 종료됩니다. 다음 참가자는 인간 화면에서 새 방을 만들고 다시 실행하세요.'
    if ($DryRun) { Write-Host 'Dry-run: 실제 타일 클릭과 제출을 하지 않고 서버 준비도 자동으로 알리지 않습니다.' }
    & $pythonPath @runnerArguments
    exit $LASTEXITCODE
}
finally { Pop-Location }
