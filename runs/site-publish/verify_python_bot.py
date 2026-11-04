"""Non-UI check of the production room adapter; no pixels/ready/submit/admin."""
import importlib.util
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('booth_cli_verification', root / 'scripts/run_booth_bot.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

report = {
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'Actual PublicRoomSession join/view on published version2; no UI, ready, images, admin or submit',
    'user_agent': cli.BOOTH_USER_AGENT,
    'role_tokens_and_room_identifiers_persisted': False,
    'model_inference_performed': False,
    'screen_capture_performed': False,
    'mouse_control_performed': False,
}
try:
    request = Request('https://human.marulee.dev/api/rooms', data=b'{}', headers={
        'Accept': 'application/json', 'Content-Type': 'application/json',
        'User-Agent': 'AlphaCaptchaDeploymentAudit/1.0',
    })
    with urlopen(request, timeout=15) as response:
        created = json.load(response)
        report['human_create_http_status'] = response.status
    # All returned capabilities are kept in process memory and never printed.
    session = cli.PublicRoomSession('https://bot.marulee.dev', created['code'])
    state = session.view()
    report.update({
        'same_room_confirmed': session.room_id == created['roomId'],
        'bot_join_and_view_succeeded': True,
        'public_state_fields': sorted(state),
        'phase': state.get('phase'),
        'all_passed': session.room_id == created['roomId'] and state.get('phase') == 'lobby'
            and set(state) == {'phase', 'roundId', 'startAt'},
    })
except HTTPError as error:
    report.update({'all_passed': False, 'http_error_status': error.code})
except Exception as error:
    report.update({'all_passed': False, 'error_type': type(error).__name__})
output = root / 'runs/site-publish/python-bot-http-verification.json'
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
raise SystemExit(0 if report.get('all_passed') else 1)
