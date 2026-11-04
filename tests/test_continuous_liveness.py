"""Pure status projection tests; no HTTP, GPU, pairing or live engine input."""

import importlib.util
import json
from pathlib import Path
import unittest


def load_audit():
    path = Path(__file__).resolve().parents[1] / "scripts/verify_continuous_booth.py"
    spec = importlib.util.spec_from_file_location("continuous_liveness_fixture", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def state(*, connected=False, first=False, ready=False, number=0, phase="lobby"):
    return {"roundNumber": number, "phase": phase, "bot": {"ready": ready},
            "remote": {"engineConnected": connected, "engineHeartbeatReceived": first, "engineStage": "ready"},
            "code": "PAIRING_SECRET", "roomId": "ROOM_SECRET", "token": "CAPABILITY_SECRET"}


class LivenessTests(unittest.TestCase):
    def setUp(self):
        self.audit = load_audit()

    def test_waiting_for_first_heartbeat_is_not_post_ready_disconnect(self):
        recorder = self.audit.LivenessRecorder(clock=lambda: 10.0)
        recorder.observe("A", state())
        recorder.observe("A", state(connected=True, first=True, ready=True))
        self.assertTrue(all(recorder.checks.values()))
        self.assertEqual([sample["firstHeartbeat"] for sample in recorder.samples], [False, True])

    def test_post_ready_disconnect_stays_failed_after_recovery(self):
        recorder = self.audit.LivenessRecorder()
        recorder.observe("A", state(connected=True, first=True, ready=True))
        recorder.observe("A", state(connected=False, first=True))
        recorder.observe("A", state(connected=True, first=True, ready=True))
        self.assertFalse(recorder.checks["no_disconnect_after_ready"])

    def test_each_lane_tracks_first_ready_independently(self):
        recorder = self.audit.LivenessRecorder()
        recorder.observe("A", state(connected=True, first=True, ready=True))
        recorder.observe("B", state())
        self.assertTrue(recorder.checks["no_disconnect_after_ready"])
        self.assertEqual(recorder.ready_lanes, {"A"})

    def test_next_participant_does_not_reset_connection_requirement(self):
        recorder = self.audit.LivenessRecorder()
        recorder.observe("A", state(connected=True, first=True, ready=True, number=1, phase="result"))
        recorder.observe("A", state(connected=False, first=True, ready=False, number=1, phase="lobby"))
        self.assertFalse(recorder.checks["no_disconnect_after_ready"])

    def test_missing_first_heartbeat_flag_fails_contract_and_is_not_guessed(self):
        recorder = self.audit.LivenessRecorder()
        missing = state(connected=True, ready=True)
        del missing["remote"]["engineHeartbeatReceived"]
        recorder.observe("A", missing)
        self.assertFalse(recorder.checks["liveness_flag_received"])
        self.assertFalse(recorder.checks["no_disconnect_after_ready"])
        self.assertIsNone(recorder.samples[0]["firstHeartbeat"])

    def test_samples_are_bounded_public_projection_with_relative_observation_times(self):
        times = iter([100.0, 100.25])
        recorder = self.audit.LivenessRecorder(clock=lambda: next(times))
        recorder.observe("A", state())
        self.assertEqual(set(recorder.samples[0]), {"relative_seconds", "lane", "roundNumber", "phase", "stage", "connected", "firstHeartbeat"})
        self.assertEqual(recorder.samples[0]["relative_seconds"], 0.25)
        self.assertNotIn("SECRET", json.dumps(recorder.samples))


if __name__ == "__main__":
    unittest.main()
