"""Summarize measured scope without changing the original failed QA report."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
directory = root / 'runs/reliability-public-20261101-v1'
original = json.loads((directory / 'verification.json').read_text(encoding='utf-8'))
acceptance_path = root / 'runs/reliability-public-20261101-acceptance.json'
acceptance = json.loads(acceptance_path.read_text(encoding='utf-8'))
acceptance['selection_interval_measurement'] = {
    'status': 'not_observed_no_multiselection',
    'actual_http_interval_samples': original['selection_timing']['actual_http_interval_samples'],
    'scheduled_interval_samples': original['selection_timing']['scheduled_interval_samples'],
    'note': 'Empty/per-single-tile plans provide no consecutive interval samples; vacuous true checks are not a timing measurement. Server/localhost tests separately validate the 250ms schedule.'}
rounds = []
for path in sorted(directory.glob('lane-*-game-*.json')):
    report = json.loads(path.read_text(encoding='utf-8'))
    rounds.append({
        'report': path.relative_to(root).as_posix(), 'lane': report['lane'],
        'condition': report['condition'], 'selected_indices': report['selected_indices'],
        'status': report['status'], 'predictions': report['model_predictions_per_game'],
        'logical_submissions': report['logical_submission_count'], 'image_barrier_used': report['image_barrier_used'],
        'prestart_image_download_seconds': report['prestart_image_download_seconds'],
        'image_ready_ack_count': report['image_ready_ack_count'],
        'during_game_image_download_seconds': report['public_image_download_during_game_seconds'],
        'prestart_challenge_inference_count': report['prestart_inference_count'],
        'image_cache_reused': report['image_cache_reused'], 'model_inference_seconds': report['model_inference_seconds'],
        'plan_upload_round_trip_seconds': report['plan_upload_ack_seconds'] - report['plan_upload_sent_seconds'],
        'request_to_common_start_seconds': report['server_request_to_common_start_seconds']})
acceptance['actual_cuda_rounds'] = rounds
acceptance['startup'] = {'model_loading_seconds': original['models_loaded_once_seconds'],
                         'synthetic_warmup': original['synthetic_warmup']}
acceptance['targeted_output_equivalence'] = original['targeted_inference_equivalence']
acceptance['liveness_sample_count'] = original['liveness_sample_count']
acceptance['preparation_latency_audit'] = {
    'A2_request_to_common_start_seconds': rounds[1]['request_to_common_start_seconds'],
    'serial_QA_control_observation_gap_seconds': 128.578 - 111.781,
    'gap_between': 'Last B1 observation at111.781 to first A2 loading observation at128.578, in the serial HTTP/PIL stand-in driver.',
    'A2_first_loading_observation_to_countdown_seconds': 132.188 - 128.578,
    'A2_first_loading_observation_to_playing_seconds': 133.266 - 128.578,
    'evidence': 'PC cache ACK completed before the late display-driver observation. That first display snapshot still had human/bot ready false; the server did not start prematurely. All three ready were observed only on countdown.',
    'attribution_limit': 'Original liveness timestamps were recorded after GET plus two page-registration POSTs; the16.797s gap cannot be assigned to one server request, network phase, or registration operation. Independent real browsers were not used. This is not a normal-preparation speed claim.',
    'future_probe_improvement': 'The QA script now records bounded per-route HTTP durations without IDs/tokens to distinguish request stalls from serial control gaps.'}
acceptance['accuracy_estimate'] = None
acceptance_path.write_text(json.dumps(acceptance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(acceptance, ensure_ascii=False))
