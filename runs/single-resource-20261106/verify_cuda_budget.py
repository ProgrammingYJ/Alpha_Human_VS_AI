"""Compare unchanged saved-RGB decisions under an explicit 30% time budget.

No answer bank, training, live rooms or global GPU/driver settings are used.
The NVIDIA sampler measures the whole device, not a per-process hardware quota.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
CONDITIONS = ({"task_type": "building_present"}, {"task_type": "pond_present"},
              {"task_type": "person_count", "operator": "gte", "n": 3},
              {"task_type": "tree_count", "operator": "gte", "n": 3})

def difference(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return max((difference(a[key], b[key]) for key in a), default=0.) if a.keys() == b.keys() else float("inf")
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        return max((difference(x, y) for x, y in zip(a, b)), default=0.) if len(a) == len(b) else float("inf")
    if type(a) is bool or a is None: return 0. if a == b else float("inf")
    if isinstance(a, (float, int)) and isinstance(b, (float, int)): return abs(a - b)
    return 0. if a == b else float("inf")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        print("Dry-run: no CUDA, models, telemetry or process changes."); return 0
    if args.output.exists(): parser.error("Preserve existing results; choose a new report")
    inventory = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command",
        "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*Alpha-Captcha-AI*run_remote_engine.py*' }).Count"], text=True)
    if int(inventory.strip()): raise RuntimeError("operator_engine_active")
    spec = importlib.util.spec_from_file_location("operator_settings", ROOT / "scripts/run_remote_engine.py")
    cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
    settings = SimpleNamespace(cpu_threads=4)
    cli.configure_runtime(settings)
    import torch
    from PIL import Image
    from alpha_captcha.inference import TorchTilePredictor
    from alpha_captcha.remote_engine import SharedModels
    from alpha_captcha.tree_model import TreeCountPredictor

    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "passed": False,
              "fixed_conditions_before_inference": CONDITIONS, "repetitions": 3,
              "single_worker": True, "target_gpu_duty_cycle": .3,
              "runtime_cpu_settings": settings.runtime_cpu_settings,
              "hardware_GPU_quota": False, "VRAM_fraction_limit": None,
              "model_or_threshold_changes": False, "answer_bank_read": False,
              "training": False, "live_rooms": False, "GUI_or_OS_input": False,
              "accuracy_measurement": False, "global_GPU_settings_changed": False,
              "device": torch.cuda.get_device_name(0), "cases": []}
    paths = sorted(p for p in (ROOT / "data/booth/public-web-v3/images").iterdir()
                   if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})[:9]
    if len(paths) != 9: raise RuntimeError("nine_fixed_public_photos_required")
    report["image_sha256"] = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    images = []
    for path in paths:
        with Image.open(path) as source:
            rgb = Image.new("RGB", source.size); rgb.paste(source.convert("RGB")); images.append(rgb)
    started = time.perf_counter()
    models = SharedModels(TorchTilePredictor.from_checkpoints(
        ROOT / "models/checkpoints/presence-limited-v1/presence.pt",
        ROOT / "models/checkpoints/person-limited-v1/person.pt", device="cuda"),
        TreeCountPredictor(ROOT / "models/pretrained/grounding-dino-tiny", device="cuda"),
        execution_mode="single", gpu_duty_cycle=.3)
    report["load_seconds"] = time.perf_counter() - started
    report["warmup"] = models.warm_up()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sampler_path = args.output.with_suffix(".device-samples.csv")
    sampler_file = sampler_path.open("w", encoding="utf-8")
    sampler = subprocess.Popen(["nvidia-smi", "--query-gpu=timestamp,utilization.gpu,memory.used", "--format=csv,noheader,nounits", "-lms", "100"],
        stdout=sampler_file, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        for condition in CONDITIONS:
            case = {"condition": condition, "unlimited": [], "budget_30": []}
            for duty, name in ((1.0, "unlimited"), (.3, "budget_30")):
                models.gpu_duty_cycle = duty  # Quiescent, finite predeclared comparison; weights unchanged.
                torch.cuda.synchronize(); torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
                for _ in range(3):
                    timings = {}; started = time.perf_counter()
                    result = models.infer(images, condition, timings=timings, clock=time.perf_counter)
                    case[name].append({"output": result, "seconds": time.perf_counter() - started, "timings": timings,
                                       "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                                       "peak_reserved_bytes": torch.cuda.max_memory_reserved()})
            reference = case["unlimited"][0]["output"]
            case["selected_equal"] = all(row["output"][0] == reference[0] for key in ("unlimited", "budget_30") for row in case[key])
            case["maximum_output_difference"] = max(difference(reference, row["output"]) for key in ("unlimited", "budget_30") for row in case[key])
            case["budget_observed_fraction_max"] = max(row["timings"]["resource_work_fraction_observed"] for row in case["budget_30"])
            case["unlimited_median_seconds"] = statistics.median(row["seconds"] for row in case["unlimited"])
            case["budget_median_seconds"] = statistics.median(row["seconds"] for row in case["budget_30"])
            report["cases"].append(case)
            print(json.dumps({key: value for key, value in case.items() if key not in {"unlimited", "budget_30"}}), flush=True)
        report["profile"] = {"available": False, "reason": "not_requested"}
        if args.profile:
            models.gpu_duty_cycle = .3
            trace_path = args.output.with_name(args.output.stem + "-tree-trace.json")
            try:
                with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA]) as profiler:
                    start_ns = time.time_ns(); wall_start = time.perf_counter()
                    profile_timings = {}; models.infer(images, CONDITIONS[3], timings=profile_timings, clock=time.perf_counter)
                    profile_wall = time.perf_counter() - wall_start
                profiler.export_chrome_trace(str(trace_path))
                trace = json.loads(trace_path.read_text(encoding="utf-8"))
                kernels = sorted((event["ts"], event["ts"] + event["dur"]) for event in trace.get("traceEvents", [])
                                 if event.get("ph") == "X" and "kernel" in str(event.get("cat", "")).lower() and event.get("dur", 0) > 0)
                busy_us = 0.; end = float("-inf")
                for left, right in kernels:
                    busy_us += max(0., right - max(left, end)); end = max(end, right)
                report["profile"] = {"available": bool(kernels), "kernel_count": len(kernels),
                    "busy_kernel_union_seconds": busy_us / 1e6, "profiled_infer_wall_seconds": profile_wall,
                    "kernel_busy_fraction_in_profiled_call": busy_us / 1e6 / profile_wall,
                    "cooperative_metrics": profile_timings, "trace_file": trace_path.name,
                    "same_process_CUDA_trace_not_whole_device": True,
                    "profile_overhead_excluded_from_unprofiled_medians": True}
            except Exception as error:
                report["profile"] = {"available": False, "error_type": type(error).__name__}
        report["passed"] = all(case["selected_equal"] and case["maximum_output_difference"] <= 1e-5
                               and case["budget_observed_fraction_max"] <= .300001 for case in report["cases"])
        report["oom"] = False
    except Exception as error:
        report.update(passed=False, error_type=type(error).__name__, oom=isinstance(error, torch.cuda.OutOfMemoryError))
        raise
    finally:
        sampler.terminate()
        try: sampler.wait(timeout=5)
        except subprocess.TimeoutExpired: sampler.kill(); sampler.wait()
        sampler_file.close()
        for image in images: image.close()
        samples = []
        for line in sampler_path.read_text(encoding="utf-8").splitlines():
            parts = line.split(",")
            try: samples.append({"timestamp": parts[0].strip(), "utilization_percent": float(parts[1]), "device_memory_used_MiB": float(parts[2])})
            except (ValueError, IndexError): pass
        report["device_samples"] = {"sample_count": len(samples), "scope": "whole device, includes desktop/other apps and both test profiles",
            "utilization_mean_percent": statistics.mean(row["utilization_percent"] for row in samples) if samples else None,
            "utilization_peak_percent": max((row["utilization_percent"] for row in samples), default=None),
            "device_memory_peak_MiB": max((row["device_memory_used_MiB"] for row in samples), default=None),
            "not_a_per_process_or_hardware_cap_measurement": True, "file": sampler_path.name}
        args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "oom": report["oom"], "device_samples": report["device_samples"], "profile": report["profile"]}), flush=True)
    return 0 if report["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
