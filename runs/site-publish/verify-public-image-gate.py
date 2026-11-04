"""Narrow public readiness protocol probe; real pixels, no ML/answer/selection."""
from pathlib import Path
import importlib.util
import json
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener

from alpha_captcha.remote_engine import ControlledTransport, EngineRoom, HeartbeatPump, NoRedirect

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("readiness_display_probe", ROOT / "scripts/verify_continuous_booth.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def main():
    target = ROOT / 'runs/reliability-public-20261101-gate-v2.json'
    if target.exists(): raise RuntimeError('new_output_required')
    transport = ControlledTransport('https://bot.marulee.dev')
    def request(path, *, token=None, body=None):
        headers = {'User-Agent': 'AlphaCaptchaImageGateQA/1.0'}
        if token: headers['Authorization'] = 'Bearer ' + token
        if body is not None: headers['Content-Type'] = 'application/json'
        req = Request(transport.origin + path, headers=headers,
                      data=None if body is None else json.dumps(body).encode('utf-8'))
        with build_opener(NoRedirect()).open(req, timeout=15) as response:
            return json.loads(response.read(262145))
    displays = AUDIT.ReadinessDisplays(request, transport, slow_human_seconds=3.0)
    pump, images, cancelled = None, [], False
    checks = {}
    try:
        created = request('/api/rooms', body={'mode': 'remote', 'lane': 'A'})
        viewer = request('/api/rooms/join', body={'role': 'bot', 'lane': 'A', 'code': created['code']})
        pair = {'path': '/api/rooms/' + created['roomId'], 'human': created['token'], 'viewer': viewer['token']}
        room = EngineRoom(transport, 'A', created['code'])
        pump = HeartbeatPump(room); pump.bind(room.view()); pump.start()
        ready = request(pair['path'], token=pair['human'])
        request(pair['path'] + '/start', token=pair['human'], body={'expectedRevision': ready['revision']})
        queued = room.view(); pump.set_stage('reserved', snapshot=queued)
        current = room.begin(queued.start_request['id'], queued.round_number)
        pump.set_stage('loading_images', snapshot=current)
        images = room.pixels(current)
        checks['engine_decoded_nine_rgb'] = len(images) == 9 and all(image.mode == 'RGB' for image in images)
        acknowledged = None
        stop_at = time.monotonic() + 40
        hold_started = hold_ended = None
        while time.monotonic() < stop_at:
            current = room.view()
            if current.phase == 'loading' and acknowledged != current.image_load_id:
                try:
                    response = room.images_ready(current)
                except Exception as error:
                    if getattr(error, 'code', None) != 'image_load_changed': raise
                else:
                    acknowledged = current.image_load_id
                    pump.set_stage('images_ready', snapshot=response)
            state = request(pair['path'], token=pair['viewer'])
            displays.observe('A', pair, state)
            item = displays.roles.get(('A', 'human', state['roundId']), {})
            if item.get('hold_until') and hold_started is None:
                hold_started = item['hold_until'] - displays.slow_human_seconds
            if state['phase'] in ('countdown', 'playing'):
                hold_ended = time.monotonic()
                checks['common_countdown_only_after_all_three_ready'] = all(state['imageLoad'][key + 'Ready'] for key in ('human', 'bot', 'engine'))
                checks['released_common_clock'] = state['startAt'] is not None and state['deadlineAt'] == state['startAt'] + 90000
                # This probe never selects or submits. End its preparation
                # while still before the common start, keeping QA isolated.
                try:
                    result = request(pair['path'] + '/cancel-start', token=pair['human'], body={'requestId': state['startRequest']['id']})
                    cancelled = result['state']['phase'] == 'lobby'
                except HTTPError as error:
                    if error.code != 409: raise
                break
            time.sleep(.2)
        else:
            raise RuntimeError('readiness_gate_timeout')
        checks.update(displays.checks)
        checks['both_display_roles_decoded_nine'] = len(displays.completed) == 2 and all(row['decoded'] == 9 for row in displays.completed)
        checks['held_after_other_roles_ready_at_least_three_seconds'] = hold_started is not None and hold_ended - hold_started >= 3
        checks['prestart_cancelled_without_gameplay'] = cancelled
        report = {'passed': all(checks.values()), 'checks': checks,
                  'readiness_displays': displays.completed, 'held_human_samples': displays.held_samples,
                  'observed_hold_seconds': None if hold_started is None else hold_ended - hold_started,
                  'ml_inference_count': 0, 'selection_count': 0, 'submission_count': 0,
                  'private_answer_or_admin_access': False, 'os_or_browser_automation_used': False,
                  'limits': 'Public API/PIL readiness test only; no model, browser rendering or physical GPU reservation measurement.'}
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        original_path = ROOT / 'runs/reliability-public-20261101-v1/verification.json'
        original = json.loads(original_path.read_text(encoding='utf-8'))
        original_failures = [key for key, value in original['checks'].items() if value is not True]
        combined = {'passed': original_failures == ['slow_human_gate_observed'] and report['passed'],
                    'original_run': 'runs/reliability-public-20261101-v1/verification.json',
                    'original_run_passed': original['passed'], 'original_checks_passed': sum(value is True for value in original['checks'].values()),
                    'original_checks_total': len(original['checks']), 'original_failed_checks': original_failures,
                    'original_false_reason': 'The first fixture held human ready from its own decode completion, ending before the other two roles were observed ready. Original report is preserved unchanged.',
                    'supplemental_run': target.relative_to(ROOT).as_posix(), 'supplemental_checks_passed': sum(value is True for value in checks.values()),
                    'supplemental_checks_total': len(checks),
                    'acceptance_note': 'Three actual CUDA rounds and output equivalence passed in the original run; the corrected narrow gate probe validates the previously unobserved slow-human gate. Does not claim the original run passed.',
                    'browser_rendering_verified': False, 'accuracy_estimate': None}
        (ROOT / 'runs/reliability-public-20261101-acceptance.json').write_text(json.dumps(combined, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'gate': report, 'combined': combined}, ensure_ascii=False))
        return 0 if combined['passed'] else 1
    finally:
        if pump is not None: pump.close()
        for image in images: image.close()
        displays.close(); transport.close()


if __name__ == '__main__': raise SystemExit(main())
