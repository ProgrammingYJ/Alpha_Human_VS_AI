"""Inspect this interpreter, installed packages and optional CUDA operation.

Does not capture the screen or control input. Pi display compatibility is only
reported; real capture/click checks still require the target device.
"""

import argparse
import importlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="write the JSON result to this path")
    parser.add_argument("--training", action="store_true", help="require training/export packages")
    parser.add_argument("--require-cuda", action="store_true", help="fail unless a CUDA tensor operation succeeds")
    args = parser.parse_args()
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "interpreter": sys.executable,
        "system": platform.system(),
        "machine": platform.machine(),
        "bits": struct.calcsize("P") * 8,
        "virtual_environment": sys.prefix != sys.base_prefix,
        "packages": {},
        "display": {
            "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
            "display_variable_present": bool(os.environ.get("DISPLAY")),
            "screen_capture_tested": False,
            "mouse_control_tested": False,
            "calibration_tested": False,
        },
        "cuda": {"available": False, "tensor_check_passed": False},
        "warnings": [],
        "errors": [],
    }
    if result["bits"] != 64:
        result["errors"].append("A 64-bit interpreter is required for the planned ONNX deployment.")
    packages = [
        ("numpy", "numpy"), ("Pillow", "PIL"),
        ("onnxruntime", "onnxruntime"), ("mss", "mss"),
        ("PyAutoGUI", "pyautogui"), ("PyYAML", "yaml"),
    ]
    training = [("torch", "torch"), ("torchvision", "torchvision"), ("onnx", "onnx")]
    if args.training:
        packages.extend(training)
    elif importlib.util.find_spec("torch") is not None:
        packages.append(("torch", "torch"))
    imported = {}
    for distribution, module_name in packages:
        entry = {"version": None, "import": "not-checked"}
        result["packages"][distribution] = entry
        try:
            entry["version"] = importlib.metadata.version(distribution)
            if module_name == "pyautogui" and platform.system() == "Linux":
                if os.environ.get("XDG_SESSION_TYPE") == "wayland" or not os.environ.get("DISPLAY"):
                    entry["import"] = "skipped-display-session-unverified"
                    result["warnings"].append("PyAutoGUI input is unverified for Wayland/headless Linux; select and test a Pi adapter on the real device.")
                    continue
            imported[module_name] = importlib.import_module(module_name)
            entry["import"] = "ok"
        except Exception as error:
            entry["import"] = "failed"
            result["errors"].append(f"{distribution}: {type(error).__name__}: {error}")
    ort = imported.get("onnxruntime")
    if ort is not None:
        result["onnxruntime_providers"] = ort.get_available_providers()
        if "CPUExecutionProvider" not in result["onnxruntime_providers"]:
            result["errors"].append("ONNX Runtime CPUExecutionProvider is unavailable.")
    torch = imported.get("torch")
    if torch is not None:
        result["cuda"]["pytorch_cuda_version"] = torch.version.cuda
        try:
            result["cuda"]["available"] = torch.cuda.is_available()
            if result["cuda"]["available"]:
                value = (torch.ones(4, device="cuda") * 3).sum().item()
                torch.cuda.synchronize()
                result["cuda"]["device_name"] = torch.cuda.get_device_name(0)
                result["cuda"]["device_memory_mib"] = round(torch.cuda.get_device_properties(0).total_memory / 1024**2)
                result["cuda"]["tensor_check_passed"] = value == 12
                if value != 12:
                    result["errors"].append("The CUDA tensor operation returned an unexpected value.")
        except Exception as error:
            result["errors"].append(f"CUDA tensor operation failed: {type(error).__name__}: {error}")
    if args.require_cuda and not result["cuda"]["tensor_check_passed"]:
        result["errors"].append("--require-cuda requested, but a CUDA tensor operation did not pass.")
    result["warnings"].append("Package checks do not establish model accuracy or Pi performance. No trained model is present in this scaffold.")
    result["ok"] = not result["errors"]
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
