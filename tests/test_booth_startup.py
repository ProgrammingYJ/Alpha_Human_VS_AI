"""Startup failures and readiness ordering, without native GUI/network/weights."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from PIL import Image
from alpha_captcha.booth_bot import BoothBotRunner, BoothLayout, BoothScreenChanged


ROOT = Path(__file__).resolve().parents[1]


def cli_module():
    spec = importlib.util.spec_from_file_location('booth_startup_fixture', ROOT / 'scripts/run_booth_bot.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def layout(calibrated=True):
    return {'url': 'https://bot.marulee.dev/', 'expected_window_title': 'ALPHA BOT | CAPTCHA',
            'calibrated': calibrated, 'grid': {'left': 10, 'top': 10, 'width': 60, 'height': 60,
             'rows': 3, 'columns': 3, 'gap_x': 3, 'gap_y': 3},
            'submit': {'x': 95, 'y': 95},
            'question_guard': {'left': 10, 'top': 0, 'width': 30, 'height': 8}}


class BoothStartupTests(unittest.TestCase):
    def test_uncalibrated_execute_stops_before_models_native_gui_or_output(self):
        cli = cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config, output = root / 'layout.json', root / 'run'
            config.write_text(json.dumps(layout(False)), encoding='utf-8')
            args = ['run_booth_bot.py', '--config', str(config), '--output', str(output),
                    '--execute', '--task', 'building_present']
            with patch('sys.argv', args), patch('sys.stderr', new_callable=io.StringIO), \
                    patch.object(cli.TorchTilePredictor, 'from_checkpoints') as model, \
                    patch.object(cli, 'PyAutoGuiScreen') as screen:
                with self.assertRaises(SystemExit) as caught:
                    cli.main()
            self.assertEqual(caught.exception.code, 2)
            model.assert_not_called(); screen.assert_not_called()
            self.assertFalse(output.exists())

    def test_model_startup_failure_writes_a_sanitized_report_without_touching_gui(self):
        cli = cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config, output = root / 'layout.json', root / 'run'
            config.write_text(json.dumps(layout()), encoding='utf-8')
            args = ['run_booth_bot.py', '--config', str(config), '--output', str(output),
                    '--execute', '--task', 'building_present']
            with patch('sys.argv', args), patch('sys.stdout', new_callable=io.StringIO), \
                    patch.object(cli.TorchTilePredictor, 'from_checkpoints',
                                 side_effect=FileNotFoundError('do-not-log-private-details')), \
                    patch.object(cli, 'PyAutoGuiScreen') as native:
                self.assertEqual(cli.main(), 1)
            native.assert_not_called()
            report = json.loads((output / 'aborted.json').read_text(encoding='utf-8'))
            self.assertEqual(report['stage'], 'model_loading')
            self.assertEqual(report['error_type'], 'FileNotFoundError')
            self.assertNotIn('do-not-log', json.dumps(report))

    def test_duplicate_bot_connection_reports_a_safe_public_code_without_response_secrets(self):
        cli = cli_module()
        secret = 'private-capability-must-not-be-shown'
        error = HTTPError('https://bot.marulee.dev/api/rooms/join', 409, 'Conflict', {},
                          io.BytesIO(json.dumps({'code': 'bot_already_connected', 'token': secret}).encode()))
        with patch.object(cli, 'urlopen', side_effect=error), self.assertRaises(cli.BoothConnectionError) as caught:
            cli.PublicRoomSession('https://bot.marulee.dev', 'ABCD2345')
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(caught.exception.code, 'bot_already_connected')
        self.assertNotIn(secret, str(caught.exception))
        self.assertIn('새 대결방', str(caught.exception))

    def test_ready_requires_a_calibrated_foreground_surface_and_in_screen_submit(self):
        class Screen:
            def __init__(self): self.captures = 0
            def title(self): return 'ALPHA BOT | CAPTCHA'
            def capture(self):
                self.captures += 1
                return Image.new('RGB', (90, 90))
        screen = Screen()
        runner = BoothBotRunner(object(), screen, BoothLayout.from_dict(layout()))
        with self.assertRaisesRegex(ValueError, 'submit'):
            runner.check_ready_surface()
        self.assertEqual(screen.captures, 1)
        runner.layout = BoothLayout.from_dict(layout(False))
        with self.assertRaisesRegex(ValueError, 'calibrated'):
            runner.check_ready_surface()
        self.assertEqual(screen.captures, 1)

    def test_ready_window_wait_has_a_bounded_deadline_and_never_clicks(self):
        cli = cli_module()
        class Clock:
            now = 0.0
            def __call__(self): return self.now
            def sleep(self, seconds): self.now += seconds
        class Runner:
            checks = 0
            def check_ready_surface(self):
                self.checks += 1
                raise BoothScreenChanged('unrelated foreground')
        clock, runner = Clock(), Runner()
        with self.assertRaises(BoothScreenChanged):
            cli.wait_for_ready_surface(runner, timeout=0.5, clock=clock, sleep=clock.sleep)
        self.assertEqual(clock.now, 0.5)
        self.assertGreaterEqual(runner.checks, 2)

    def test_dry_run_cannot_advertise_automatic_execution_readiness(self):
        cli = cli_module()
        args = ['run_booth_bot.py', '--config', 'not-read.json', '--output', 'unused',
                '--ready', '--room', 'ABCD2345', '--tree-model', 'grounding-dino']
        with patch('sys.argv', args), patch('sys.stderr', new_callable=io.StringIO), \
                patch.object(cli.TorchTilePredictor, 'from_checkpoints') as model, \
                patch.object(cli, 'PyAutoGuiScreen') as screen:
            with self.assertRaises(SystemExit) as caught:
                cli.main()
        self.assertEqual(caught.exception.code, 2)
        model.assert_not_called(); screen.assert_not_called()

    def test_automatic_ready_follows_all_models_and_the_actual_surface_check(self):
        cli = cli_module()
        events = []
        class Tree:
            def __init__(self, **kwargs): pass
            def prepare(self): events.append('tree_model')
        class Session:
            def __init__(self, *args): events.append('join')
            def open_browser(self, path): events.append('open')
            def set_ready(self, flag): events.append('ready' if flag else 'unready')
            def view(self):
                return {'phase': 'playing', 'roundId': 'public-round', 'startAt': 0,
                        'condition': {'task_type': 'building_present'}}
        class Runner:
            def __init__(self, *args, **kwargs): pass
            def check_ready_surface(self): events.append('surface')
            def run_once(self, *args, **kwargs):
                events.append('infer')
                return {'selected_tiles': [], 'submit_performed': True}, Image.new('RGB', (60, 60)), None
        def load(*args, **kwargs): events.append('presence_person_models'); return object()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / 'layout.json'
            config.write_text(json.dumps(layout()), encoding='utf-8')
            args = ['run_booth_bot.py', '--config', str(config), '--output', str(root / 'run'),
                    '--room', 'ABCD2345', '--base-url', 'https://bot.marulee.dev', '--execute',
                    '--ready', '--open-browser', '--tree-model', 'grounding-dino', '--render-wait-seconds', '0']
            with patch('sys.argv', args), patch('sys.stdout', new_callable=io.StringIO), \
                    patch.object(cli.TorchTilePredictor, 'from_checkpoints', side_effect=load), \
                    patch.object(cli, 'LazyTreePredictor', Tree), patch.object(cli, 'PyAutoGuiScreen', return_value=object()), \
                    patch.object(cli, 'PublicRoomSession', Session), patch.object(cli, 'BoothBotRunner', Runner):
                self.assertEqual(cli.main(), 0)
        self.assertEqual(events, ['presence_person_models', 'tree_model', 'join', 'open', 'surface', 'ready', 'infer'])


if __name__ == '__main__':
    unittest.main()
