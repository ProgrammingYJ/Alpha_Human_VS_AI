"""Operator admission tests use mocked models/transports, never real pairing."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run_remote_engine.py"
CODE = "ABCDEFGH"
OTHER_CODE = "HGFEDCBA"


def cli_module():
    spec = importlib.util.spec_from_file_location("single_operator_fixture", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SingleOperatorTests(unittest.TestCase):
    def test_initial_B_is_rejected_before_loading_network_or_output_creation(self):
        for options, supplied in ((["--room-b", CODE], ""),
                                  (["--rooms-stdin"], json.dumps({"B": CODE}) + "\n")):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as directory:
                cli, printed, output = cli_module(), StringIO(), Path(directory) / "never-created"
                with patch("sys.argv", [str(SCRIPT), "--execute", "--output", str(output), *options]), \
                     patch("sys.stdin", StringIO(supplied)), \
                     patch.object(cli, "load_models") as load, patch.object(cli, "ControlledTransport") as transport, \
                     redirect_stdout(printed), redirect_stderr(printed):
                    with self.assertRaises(SystemExit) as error:
                        cli.main()
                self.assertEqual(error.exception.code, 2)
                load.assert_not_called(); transport.assert_not_called()
                self.assertFalse(output.exists())
                self.assertNotIn(CODE, printed.getvalue())

    def test_single_console_accepts_bare_A_code_blocks_B_and_never_logs_codes(self):
        cli, calls, printed = cli_module(), [], StringIO()
        class Controller:
            def __init__(self, *args, **kwargs):
                self.reports = []
            def add(self, lane, code): calls.append(("add", lane, code))
            def stop(self, lane): calls.append(("stop", lane))
            def close(self): calls.append(("close",))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            commands = [CODE, "B " + OTHER_CODE, "stop A", "A " + OTHER_CODE, "stop", "quit"]
            with patch("sys.argv", [str(SCRIPT), "--execute", "--output", str(output)]), \
                 patch.object(cli, "load_models", return_value=object()) as load, \
                 patch.object(cli, "ControlledTransport", return_value=MagicMock()), \
                 patch.object(cli, "EngineController", Controller), \
                 patch.object(cli.getpass, "getpass", side_effect=commands), redirect_stdout(printed):
                self.assertEqual(cli.main(), 0)
            self.assertEqual(calls, [("add", "A", CODE), ("stop", "A"),
                                     ("add", "A", OTHER_CODE), ("stop", "A"), ("close",)])
            args = load.call_args.args[0]
            self.assertEqual((args.inference_mode, args.gpu_duty_cycle, args.cpu_threads), ("single", .30, 4))
            report = json.loads((output / "startup.json").read_text(encoding="utf-8"))
            self.assertEqual(report["enabled_lanes"], ["A"])
            self.assertEqual(report["resource_budget"]["gpu_duty_cycle_requested"], .30)
            self.assertFalse(report["resource_budget"]["instantaneous_gpu_quota_claimed"])
            self.assertFalse(report["resource_budget"]["vram_quota_claimed"])
            combined = printed.getvalue() + json.dumps(report)
            self.assertNotIn(CODE, combined); self.assertNotIn(OTHER_CODE, combined)

    def test_explicit_serial_mode_retains_B_without_enabling_a_second_worker(self):
        cli, added, printed = cli_module(), [], StringIO()
        class Controller:
            def __init__(self, *args, **kwargs): self.reports = [{"status": "game_ended"}]
            def add(self, lane, code): added.append((lane, code))
            def wait(self): pass
            def close(self): pass
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            with patch("sys.argv", [str(SCRIPT), "--execute", "--once", "--inference-mode", "serial", "--rooms-stdin", "--output", str(output)]), \
                 patch("sys.stdin", StringIO(json.dumps({"B": CODE}) + "\n")), \
                 patch.object(cli, "load_models", return_value=object()), \
                 patch.object(cli, "ControlledTransport", return_value=MagicMock()), \
                 patch.object(cli, "EngineController", Controller), redirect_stdout(printed):
                self.assertEqual(cli.main(), 0)
            self.assertEqual(added, [("B", CODE)])
            report = json.loads((output / "startup.json").read_text(encoding="utf-8"))
            self.assertEqual(report["enabled_lanes"], ["A", "B"])
            self.assertEqual(report["requested_inference_mode"], "serial")

    def test_invalid_resource_settings_and_parallel_budget_are_rejected_before_model_load(self):
        options = [["--gpu-duty-cycle", value] for value in ("nan", "inf", "0", "-.1", "1.01")]
        options += [["--cpu-threads", value] for value in ("0", "65")]
        options += [["--inference-mode", "parallel"]]
        for fields in options:
            with self.subTest(fields=fields), tempfile.TemporaryDirectory() as directory:
                cli, printed = cli_module(), StringIO()
                with patch("sys.argv", [str(SCRIPT), "--execute", "--output", str(Path(directory) / "run"), *fields]), \
                     patch.object(cli, "load_models") as load, patch.object(cli, "ControlledTransport") as transport, \
                     redirect_stdout(printed), redirect_stderr(printed):
                    with self.assertRaises(SystemExit) as error: cli.main()
                self.assertEqual(error.exception.code, 2)
                load.assert_not_called(); transport.assert_not_called()

    def test_budget_is_passed_to_model_scheduler_rather_than_only_reported(self):
        cli = cli_module()
        args = SimpleNamespace(presence="presence.pt", person="person.pt", tree_model_dir="tree", device="cuda",
                               inference_mode="single", gpu_duty_cycle=.30, cpu_threads=4)
        with patch.object(cli, "configure_runtime"), \
             patch("alpha_captcha.inference.TorchTilePredictor.from_checkpoints", return_value="shared-predictor"), \
             patch("alpha_captcha.tree_model.TreeCountPredictor", return_value="tree-predictor"), \
             patch.object(cli, "SharedModels") as shared:
            self.assertIs(cli.load_models(args), shared.return_value)
        shared.assert_called_once_with("shared-predictor", "tree-predictor", execution_mode="single", gpu_duty_cycle=.30)


if __name__ == "__main__": unittest.main()
