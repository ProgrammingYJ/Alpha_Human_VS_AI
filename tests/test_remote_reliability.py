"""Bounded recovery, actual loopback keepalive and unchanged question routing."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest
from unittest.mock import patch

from PIL import Image

from alpha_captcha import remote_engine as remote
from alpha_captcha.inference import TorchTilePredictor
from alpha_captcha.tasks import TaskCondition, select_tiles
from test_gpu_reservation import public, ROOM


class KeepaliveTests(unittest.TestCase):
    def test_real_loopback_reuses_connections_and_never_follows_redirect(self):
        ports, modes = [], ["ok", "ok", "redirect", "ok"]
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            def log_message(self, *args): pass
            def do_GET(self):
                ports.append(self.client_address[1])
                mode = modes.pop(0)
                data = b'{}'
                self.send_response(302 if mode == "redirect" else 200)
                if mode == "redirect": self.send_header("Location", "https://outside.invalid/secret")
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers(); self.wfile.write(data); self.wfile.flush()
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        transport = remote.ControlledTransport(f"http://127.0.0.1:{server.server_port}")
        try:
            self.assertEqual(transport.json("/api/rooms/" + ROOM), {})
            self.assertEqual(transport.json("/api/rooms/" + ROOM), {})
            self.assertEqual(ports[0], ports[1])
            with self.assertRaises(remote.RemoteEngineError) as error:
                transport.json("/api/rooms/" + ROOM)
            self.assertEqual(error.exception.status, 302)
            self.assertEqual(transport.json("/api/rooms/" + ROOM), {})
            self.assertNotEqual(ports[2], ports[3])
            self.assertEqual(transport._keepalive.requests_completed, 3)
        finally:
            transport.close(); server.shutdown(); server.server_close(); thread.join(1)

    def test_connections_are_thread_local_and_reused_within_each_thread(self):
        ports = []
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            def log_message(self, *args): pass
            def do_GET(self):
                ports.append(self.client_address[1]); raw = b'{}'
                self.send_response(200); self.send_header("Content-Length", str(len(raw)))
                self.end_headers(); self.wfile.write(raw); self.wfile.flush()
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        transport = remote.ControlledTransport(f"http://127.0.0.1:{server.server_port}")
        errors = []
        try:
            def query():
                try:
                    transport.json("/api/rooms/" + ROOM)
                    transport.json("/api/rooms/" + ROOM)
                except Exception as error: errors.append(type(error).__name__)
            query()
            other = threading.Thread(target=query); other.start(); other.join(2)
            self.assertEqual(errors, []); self.assertEqual(len(ports), 4)
            self.assertEqual(ports[0], ports[1]); self.assertEqual(ports[2], ports[3])
            self.assertNotEqual(ports[0], ports[2])
        finally:
            transport.close(); server.shutdown(); server.server_close(); thread.join(1)


class RecoveryTests(unittest.TestCase):
    def test_lobby_deployment_is_upgraded_without_losing_engine_capability(self):
        calls = []
        class Transport:
            new_server = False
            def json(self, path, *, token=None, body=None):
                current = public("lobby", request_id=None)
                if self.new_server:
                    current["remote"]["imageBarrierSupported"] = bool(body and body.get("protocolVersion") == 3)
                calls.append((path, token, body))
                return {"roomId": ROOM, "token": "x" * 43, "state": current}
        transport = Transport(); room = remote.EngineRoom(transport, "A", "ABCDEFGH")
        room.heartbeat("ready"); transport.new_server = True
        self.assertFalse(room.view().image_barrier_supported)
        room.heartbeat("ready")
        self.assertEqual(calls[-1][2]["protocolVersion"], 3)
        self.assertEqual(calls[-1][1], "x" * 43)
        self.assertEqual(sum(path.endswith("join") for path, _, _ in calls), 1)

    def test_heartbeat_observes_new_deployment_between_gets_and_upgrades_once(self):
        bodies = []
        class Transport:
            def json(self, path, *, token=None, body=None):
                current = public("lobby", request_id=None)
                if path.endswith("join"): return {"roomId": ROOM, "token": "x" * 43, "state": current}
                bodies.append(body)
                current["remote"]["imageBarrierSupported"] = body["protocolVersion"] == 3
                return {"state": current}
        room = remote.EngineRoom(Transport(), "A", "ABCDEFGH"); room.heartbeat("ready")
        self.assertEqual([body["protocolVersion"] for body in bodies], [2, 3])
        self.assertEqual(bodies[0]["roundId"], bodies[1]["roundId"])

    def test_read_only_get_retries_one_transient_failure_but_not_bad_capabilities(self):
        waits = []
        class Transport:
            failed = False
            def json(self, path, *, token=None, body=None):
                current = public("lobby", request_id=None)
                if path.endswith("join"): return {"roomId": ROOM, "token": "x" * 43, "state": current}
                if not self.failed:
                    self.failed = True; raise remote.RemoteEngineError("connection_failed")
                return current
        room = remote.EngineRoom(Transport(), "A", "ABCDEFGH", sleep=waits.append)
        self.assertEqual(room.view().phase, "lobby"); self.assertEqual(waits, [0.2])


class RoutingTests(unittest.TestCase):
    def test_condition_specific_predictions_match_full_selection_and_do_not_run_unused_model(self):
        images = [Image.new("RGB", (4, 4), (index, 0, 0)) for index in range(9)]
        predictor = TorchTilePredictor(object(), {"profile": {"threshold": .5}}, object(), object())
        scores = [{"building": .9 if i in (0, 4) else .1, "pond": .1, "tree": .1} for i in range(9)]
        people = [{"person_count": 4 if i in (2, 5) else 0} for i in range(9)]
        with patch("alpha_captcha.presence_model.predict_presence", return_value=scores) as presence, patch("alpha_captcha.person_model.predict_person", return_value=people) as person:
            full = predictor.predict_tiles(images)
            presence.reset_mock(); person.reset_mock()
            building = TaskCondition("building_present")
            targeted = predictor.predict_condition_tiles(images, building)
            self.assertEqual(select_tiles(full, building, {"building": .5}), select_tiles(targeted, building, {"building": .5}))
            person.assert_not_called(); presence.assert_called_once()
            self.assertTrue(all(row.person_count is None for row in targeted))
            presence.reset_mock(); person.reset_mock()
            condition = TaskCondition("person_count", "gte", 3)
            targeted = predictor.predict_condition_tiles(images, condition)
            self.assertEqual(select_tiles(full, condition), select_tiles(targeted, condition))
            presence.assert_not_called(); person.assert_called_once()
            self.assertTrue(all(dict(row.presence_scores) == {} for row in targeted))
        for image in images: image.close()


if __name__ == "__main__": unittest.main()
