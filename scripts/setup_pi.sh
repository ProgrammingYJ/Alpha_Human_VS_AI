#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$project_root"
python3 -c 'import platform, struct, sys; assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64") and struct.calcsize("P") == 8, "Use 64-bit ARM Linux"; assert (3, 12) <= sys.version_info[:2] < (3, 14), "Use Python 3.12 or 3.13; verify available ARM64 wheels first"'
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements/runtime.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pip check
.venv/bin/python scripts/check_env.py --report logs/environment-check-pi.json
printf '%s\n' 'Runtime package check finished. Pi inference, capture, and input still need hardware testing.'
