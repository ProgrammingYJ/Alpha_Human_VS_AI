$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        & py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 virtual environment creation failed.' }
    }
    & $venvPython -c "import sys; assert sys.version_info[:2] == (3, 12), 'Use Python 3.12 for this PC profile'"
    if ($LASTEXITCODE -ne 0) { throw 'Unexpected interpreter version.' }
    & $venvPython -m pip install -r requirements/pc-gpu.txt
    if ($LASTEXITCODE -ne 0) { throw 'PyTorch GPU package installation failed.' }
    & $venvPython -m pip install -r requirements/training.txt -c requirements/windows-py312.lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Training/runtime package installation failed.' }
    & $venvPython -m pip install --no-deps -e .
    if ($LASTEXITCODE -ne 0) { throw 'Project package installation failed.' }
    & $venvPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed.' }
    & $venvPython scripts/check_env.py --training --require-cuda --report logs/environment-check.json
    if ($LASTEXITCODE -ne 0) { throw 'Environment validation failed; inspect logs/environment-check.json.' }
    Write-Output 'PC setup passed. No model has been trained; no screen or mouse operation was performed.'
}
finally {
    Pop-Location
}
