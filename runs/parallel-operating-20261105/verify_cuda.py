"""Bounded saved-RGB verification of the actual SharedModels serial/parallel APIs.

No live rooms, answer bank, model updates or browser/OS input. Run only while
the operator engine is stopped; --execute is required to initialize CUDA.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import statistics
import subprocess
import threading
import time


ROOT = Path(__file__).resolve().parents[2]
CONDITIONS = (
    {"task_type": "building_present"},
    {"task_type": "pond_present"},
    {"task_type": "person_count", "operator": "gte", "n": 3},
    {"task_type": "tree_count", "operator": "gte", "n": 3},
)


def operator_count():
    query = "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*Alpha-Captcha-AI*run_remote_engine.py*' }).Count"
    return int(subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", query], text=True).strip())


def maximum_difference(left, right):
    if type(left) is not type(right): return 1e300
    if isinstance(left, dict):
        if left.keys() != right.keys(): return 1e300
        return max((maximum_difference(left[key], right[key]) for key in left), default=0.)
    if isinstance(left, (list, tuple)):
        if len(left) != len(right): return 1e300
        return max((maximum_difference(a, b) for a, b in zip(left, right)), default=0.)
    if isinstance(left, bool) or left is None: return 0. if left == right else 1e300
    if isinstance(left, (int, float)): return abs(left - right)
    return 0. if left == right else 1e300


def kernel_overlap(trace_path):
    """Measure overlapping complete kernel intervals on distinct trace streams.

    This uses CUPTI/Kineto timestamps, not Python call intervals. Unknown trace
    formats are reported as unavailable and never inferred from host overlap.
    """
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    intervals, streams = [], set()
    for event in trace.get("traceEvents", []):
        args = event.get("args", {})
        if event.get("ph") != "X" or "kernel" not in str(event.get("cat", "")).lower(): continue
        stream = args.get("stream", args.get("stream id"))
        if stream is None or event.get("dur", 0) <= 0: continue
        start, finish = event["ts"], event["ts"] + event["dur"]
        intervals.extend(((start, 1, str(stream)), (finish, -1, str(stream))))
        streams.add(str(stream))
    if not intervals:
        return {"available": False, "reason": "no_cuda_kernel_events_in_trace", "kernel_concurrency_observed": False}
    active, previous, concurrent_us, busy_us = {}, None, 0., 0.
    for timestamp, delta, stream in sorted(intervals):
        count = sum(value > 0 for value in active.values())
        if previous is not None:
            if count: busy_us += timestamp - previous
            if count >= 2: concurrent_us += timestamp - previous
        active[stream] = active.get(stream, 0) + delta
        previous = timestamp
    return {"available": True, "source": "Kineto CUDA kernel complete-event timestamps",
            "kernel_count": len(intervals) // 2, "cuda_trace_streams": sorted(streams),
            "gpu_busy_union_seconds": busy_us / 1e6,
            "distinct_stream_kernel_overlap_seconds": concurrent_us / 1e6,
            "kernel_concurrency_observed": concurrent_us > 0,
            "trace_contains_only_this_saved_rgb_pair": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--repetitions", type=int, choices=(1, 3), default=1)
    parser.add_argument("--profile", action="store_true", help="attempt one separate tree/tree CUDA kernel trace")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("cuda-report.json"))
    args = parser.parse_args()
    if not args.execute:
        print("Dry-run: no CUDA/model initialization, room requests or process changes.")
        return 0
    if args.output.exists(): parser.error("existing report must be preserved; specify a new --output")
    count = operator_count()
    if count: raise RuntimeError("operator_engine_active_no_gpu_verification_performed")
    import torch
    from PIL import Image
    from alpha_captcha.inference import TorchTilePredictor
    from alpha_captcha.tree_model import TreeCountPredictor
    from alpha_captcha.remote_engine import SharedModels

    if not torch.cuda.is_available(): raise RuntimeError("CUDA_unavailable")
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "operator_engine_process_count": count,
              "device": torch.cuda.get_device_name(0), "total_memory_bytes": torch.cuda.get_device_properties(0).total_memory,
              "torch_version": torch.__version__, "repetitions_per_mode_per_pair": args.repetitions,
              "condition_pairs_fixed_before_inference": [list(pair) for pair in itertools.product(CONDITIONS, repeat=2)],
              "training_or_threshold_changes": False, "answer_bank_read": False,
              "live_rooms_accessed": False, "gui_or_os_input": False,
              "accuracy_measurement": False, "gpu_percentage_partitioned": False,
              "host_overlap_is_not_kernel_overlap": True, "cases": []}
    paths = sorted(path for path in (ROOT / "data/booth/public-web-v3/images").iterdir()
                   if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})[:18]
    if len(paths) != 18: raise RuntimeError("need_18_fixed_public_RGB_images")
    report["input_rule"] = "lexicographically first 18 public-web-v3/images paths, fixed before predictions; first9 A/next9 B"
    report["image_sha256_by_lane"] = [[hashlib.sha256(path.read_bytes()).hexdigest() for path in paths[offset:offset + 9]] for offset in (0, 9)]
    images = []
    for path in paths:
        with Image.open(path) as source:
            image = source.convert("RGB").copy(); image.info.clear(); images.append(image)
    lane_images = (images[:9], images[9:])
    started = time.perf_counter()
    predictor = TorchTilePredictor.from_checkpoints(ROOT / "models/checkpoints/presence-limited-v1/presence.pt",
                                                   ROOT / "models/checkpoints/person-limited-v1/person.pt", device="cuda")
    tree = TreeCountPredictor(ROOT / "models/pretrained/grounding-dino-tiny", device="cuda")
    models = {mode: SharedModels(predictor, tree, execution_mode=mode) for mode in ("serial", "parallel")}
    report["model_load_and_worker_setup_seconds"] = time.perf_counter() - started
    report["execution_metadata"] = {mode: shared.execution_metadata() for mode, shared in models.items()}
    report["warmup"] = {mode: shared.warm_up() for mode, shared in models.items()}
    report["same_weight_objects_for_all_workers"] = all(
        worker.predictor.presence_model is predictor.presence_model
        and worker.predictor.person_model is predictor.person_model
        and worker.tree_predictor.model is tree.model for shared in models.values() for worker in shared.workers)

    def worker(shared, condition, lane, origin, gate=None):
        claim = shared.reserve()
        try:
            if gate: gate.wait(timeout=60)
            timings = {}
            call_started = time.perf_counter()
            output = shared.infer(lane_images[lane], condition, timings=timings, reservation=claim, clock=time.perf_counter)
            call_returned = time.perf_counter()
            return {"lane": "AB"[lane], "worker_index": claim.worker_index,
                    "call_started_seconds": call_started - origin, "call_returned_seconds": call_returned - origin,
                    "wall_seconds": call_returned - call_started, "output": output, "timings": timings}
        finally: claim.release()

    def pair_run(pool, shared, pair):
        torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
        origin = time.perf_counter()
        if shared.execution_mode == "parallel":
            gate = threading.Barrier(3)
            futures = [pool.submit(worker, shared, condition, lane, origin, gate) for lane, condition in enumerate(pair)]
            gate.wait(timeout=60)
            values = [future.result(timeout=120) for future in futures]
        else:
            values = [worker(shared, condition, lane, origin) for lane, condition in enumerate(pair)]
        torch.cuda.synchronize()
        wall = time.perf_counter() - origin
        overlap = max(0., min(value["call_returned_seconds"] for value in values)
                      - max(value["call_started_seconds"] for value in values))
        return {"wall_seconds": wall, "host_call_overlap_seconds": overlap,
                "peak_allocated_bytes": torch.cuda.max_memory_allocated(), "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
                "lanes": values}

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            for index, pair in enumerate(itertools.product(CONDITIONS, repeat=2), 1):
                print(f"PAIR {index}/16 {pair[0]['task_type']} + {pair[1]['task_type']}", flush=True)
                case = {"conditions": list(pair), "serial": [], "parallel": []}
                for mode in ("serial", "parallel"):
                    for _ in range(args.repetitions): case[mode].append(pair_run(pool, models[mode], pair))
                reference = [lane["output"] for lane in case["serial"][0]["lanes"]]
                for mode in ("serial", "parallel"):
                    for repeat in case[mode]:
                        repeat["maximum_output_difference_from_serial"] = maximum_difference(reference, [lane["output"] for lane in repeat["lanes"]])
                        repeat["selected_indices_equal_serial"] = all(a[0] == b["output"][0] for a, b in zip(reference, repeat["lanes"]))
                case["serial_median_wall_seconds"] = statistics.median(value["wall_seconds"] for value in case["serial"])
                case["parallel_median_wall_seconds"] = statistics.median(value["wall_seconds"] for value in case["parallel"])
                report["cases"].append(case)
            report["cuda_kernel_profile"] = {"available": False, "reason": "not_requested", "kernel_concurrency_observed": False}
            if args.profile:
                trace_path = args.output.with_name(args.output.stem + "-tree-tree-trace.json")
                try:
                    with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA]) as profiler:
                        pair_run(pool, models["parallel"], (CONDITIONS[3], CONDITIONS[3]))
                    profiler.export_chrome_trace(str(trace_path))
                    report["cuda_kernel_profile"] = kernel_overlap(trace_path)
                    report["cuda_kernel_profile"]["trace_file"] = trace_path.name
                except Exception as error:
                    report["cuda_kernel_profile"] = {"available": False, "reason": "profiler_failed", "error_type": type(error).__name__, "kernel_concurrency_observed": False}
        report["oom"] = False
        report["passed"] = (report["same_weight_objects_for_all_workers"] and all(
            repeat["selected_indices_equal_serial"] and repeat["maximum_output_difference_from_serial"] <= 1e-6
            for case in report["cases"] for mode in ("serial", "parallel") for repeat in case[mode]))
    except Exception as error:
        report.update(passed=False, oom=isinstance(error, torch.cuda.OutOfMemoryError), error_type=type(error).__name__)
        raise
    finally:
        for image in images: image.close()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "case_count": len(report["cases"]), "oom": report["oom"],
                      "cuda_kernel_profile": report["cuda_kernel_profile"]}), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__": raise SystemExit(main())
