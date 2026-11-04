"""Prestart pixel readiness, protocol negotiation and scoped cache regression tests."""
import unittest

from PIL import Image

from alpha_captcha import remote_engine as remote
from test_gpu_reservation import Clock, CONDITION, Predictor, Pump, REQUEST, ROOM, ROUND, public

EPOCH = "44444444-4444-4444-8444-444444444444"
NEXT_EPOCH = "55555555-5555-4555-8555-555555555555"


def barrier_state(phase="loading", *, epoch=EPOCH, ready=False):
    value = public("playing" if phase in {"loading", "countdown"} else phase)
    value["phase"] = phase
    value["remote"]["imageBarrierSupported"] = True
    value["imageLoad"] = {"id": epoch, "expiresAt": 60000,
                          "humanReady": ready, "botReady": ready, "engineReady": ready}
    if phase in {"loading", "countdown"}:
        value["preloadTiles"], value["tiles"] = value["tiles"], []
        value["topic"] = None
        value["deadlineAt"] = None if phase == "loading" else 96000
        value["startAt"] = None if phase == "loading" else 6000
    return value


class BarrierRoom:
    lane = "A"
    def __init__(self, models, clock, *, never_ready=False, reload=False, cancel=False, change_paths=False):
        self.models, self.clock = models, clock
        self.phase, self.epoch = "queued", EPOCH
        self.never_ready, self.reload, self.cancel, self.change_paths = never_ready, reload, cancel, change_paths
        self.downloads, self.acks, self.selects = 0, [], []
        self.reloaded, self.saved_images = False, []
    def view(self):
        if self.cancel and self.acks:
            return remote.PublicSnapshot.from_state(public("lobby", request_id=None), "A")
        if self.reload and self.acks and not self.reloaded and self.clock() > 2.1:
            self.epoch, self.reloaded = NEXT_EPOCH, True
        if self.phase == "loading" and self.epoch in self.acks and not self.never_ready and self.clock() >= 4:
            self.phase = "countdown"
        if self.phase == "countdown" and self.clock() >= 6:
            self.phase = "playing"
        if self.phase == "queued":
            value = public()
            value["remote"]["imageBarrierSupported"] = True
        else:
            value = barrier_state(self.phase, epoch=self.epoch, ready=self.phase != "loading")
            if self.change_paths and self.downloads:
                value["preloadTiles"][0]["url"] = "/api/photos/99999999-9999-4999-8999-999999999999"
        return remote.PublicSnapshot.from_state(value, "A")
    def heartbeat(self, *args, **kwargs): pass
    def begin(self, *args):
        if not self.models.reservations.busy:
            raise AssertionError("GPU reservation missing")
        self.phase = "loading"
        return self.view()
    def pixels(self, snapshot):
        if self.phase != "loading": raise AssertionError("timed image download")
        self.downloads += 1
        self.clock.sleep(2)
        self.saved_images = [Image.new("RGB", (4, 4)) for _ in range(9)]
        return self.saved_images
    def images_ready(self, snapshot):
        self.acks.append(snapshot.image_load_id)
        return self.view()
    def select(self, round_id, sequence, tile): self.selects.append(tile)
    def submit(self, round_id):
        self.phase = "result"
        return {"correct": True, "elapsedMs": 2000, "state": barrier_state("result")}


class ReadinessTests(unittest.TestCase):
    def run_fixture(self, **options):
        clock, predictor = Clock(), Predictor()
        models = remote.SharedModels(predictor, None)
        room = BarrierRoom(models, clock, **options)
        observed = []
        original = predictor.predict_tiles
        def predict(images):
            observed.append(clock())
            if room.phase != "playing": raise AssertionError("prestart inference")
            return original(images)
        predictor.predict_tiles = predict
        report = remote.run_one_room(room, models, clock=clock, sleep=clock.sleep,
                                     heartbeat_factory=Pump, wait_seconds=10)
        self.assertFalse(models.reservations.busy)
        self.assertFalse(models.lock.locked())
        return room, predictor, report, observed

    def test_slow_other_display_blocks_inference_and_reuses_decoded_pixels_after_start(self):
        room, predictor, report, observed = self.run_fixture()
        self.assertEqual(room.downloads, 1)
        self.assertEqual(predictor.calls, 1)
        self.assertGreaterEqual(observed[0], 6)
        self.assertEqual(report["status"], "game_ended")
        self.assertTrue(report["image_cache_reused"])
        self.assertEqual(report["prestart_image_download_seconds"], 2)
        self.assertEqual(report["public_image_download_during_game_seconds"], 0)
        with self.assertRaises(ValueError): room.saved_images[0].getpixel((0, 0))

    def test_new_browser_epoch_is_acknowledged_without_second_download_or_prediction(self):
        room, predictor, report, observed = self.run_fixture(reload=True)
        self.assertEqual(room.acks, [EPOCH, NEXT_EPOCH])
        self.assertEqual(room.downloads, 1)
        self.assertEqual(predictor.calls, 1)
        self.assertEqual(report["image_ready_ack_count"], 2)

    def test_never_ready_display_has_no_model_or_selection_and_releases_gpu(self):
        room, predictor, report, _ = self.run_fixture(never_ready=True)
        self.assertEqual(predictor.calls, 0)
        self.assertEqual(room.selects, [])
        self.assertEqual(report["error_code"], "wait_timeout")

    def test_cancelled_preload_drops_cache_and_never_infers(self):
        room, predictor, report, _ = self.run_fixture(cancel=True)
        self.assertEqual(predictor.calls, 0)
        self.assertEqual(report["status"], "start_cancelled")

    def test_changed_tile_order_cannot_reuse_cached_pixels(self):
        room, predictor, report, _ = self.run_fixture(change_paths=True)
        self.assertEqual(predictor.calls, 0)
        self.assertEqual(report["error_code"], "image_cache_changed")

    def test_new_server_bootstrap_uses_protocol_three_even_when_capabilities_initially_false(self):
        calls = []
        class Transport:
            def json(self, path, *, token=None, body=None):
                state = public("lobby", request_id=None)
                state["remote"].update(gpuReservationSupported=body is not None and path.endswith("engine"),
                                       imageBarrierSupported=body is not None and path.endswith("engine"))
                if path.endswith("join"):
                    return {"roomId": ROOM, "token": "x" * 43, "state": state}
                calls.append(body)
                return {"state": state}
        room = remote.EngineRoom(Transport(), "A", "ABCDEFGH")
        room.heartbeat("ready")
        self.assertEqual(calls[0]["protocolVersion"], 3)

    def test_new_server_without_ready_capability_cannot_be_used_as_old_server(self):
        state = public("queued")
        state["remote"]["imageBarrierSupported"] = False
        with self.assertRaises(remote.RemoteEngineError) as error:
            remote.PublicSnapshot.from_state(state, "A")
        self.assertEqual(error.exception.code, "protocol_upgrade_required")

    def test_lost_ready_ack_after_start_recovers_only_exact_server_proven_epoch(self):
        for changed in (False, True):
            with self.subTest(changed=changed):
                bodies = []
                class Transport:
                    def json(self, path, *, token=None, body=None):
                        if path.endswith("join"):
                            state = public("lobby", request_id=None)
                            state["remote"]["imageBarrierSupported"] = False
                            return {"roomId": ROOM, "token": "x" * 43, "state": state}
                        if body is None:
                            return barrier_state("playing", epoch=NEXT_EPOCH if changed else EPOCH, ready=True)
                        bodies.append(body)
                        if len(bodies) == 1: raise remote.RemoteEngineError("connection_failed")
                        raise remote.RemoteEngineError("not_loading", status=409)
                room = remote.EngineRoom(Transport(), "A", "ABCDEFGH", sleep=lambda _: None)
                snapshot = remote.PublicSnapshot.from_state(barrier_state(), "A")
                if changed:
                    with self.assertRaises(remote.RemoteEngineError) as error: room.images_ready(snapshot)
                    self.assertEqual(error.exception.code, "image_load_changed")
                else:
                    self.assertEqual(room.images_ready(snapshot).phase, "playing")
                self.assertEqual(len(bodies), 2)
                self.assertEqual(bodies[0], bodies[1])


if __name__ == "__main__": unittest.main()
