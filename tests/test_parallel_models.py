"""CPU fixtures for shared weights; no official weights or CUDA are loaded."""

from concurrent.futures import ThreadPoolExecutor
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image
import torch
from torch import nn

from alpha_captcha.inference import TorchTilePredictor
from alpha_captcha.person_model import PersonTrainingProfile, predict_person
from alpha_captcha.presence_model import predict_presence
from alpha_captcha.tasks import TaskCondition
from alpha_captcha.tree_model import TreeCountPredictor, TreeCountProfile


class PresenceFixture(nn.Module):
    def __init__(self):
        super().__init__()
        self.normalization = nn.BatchNorm2d(3)

    def forward(self, pixels):
        return self.normalization(pixels).mean(dim=(2, 3))


class PersonFixture(nn.Module):
    def __init__(self):
        super().__init__()
        self.anchor = nn.Parameter(torch.zeros(()), requires_grad=False)

    def forward(self, images):
        return [{"boxes": torch.tensor([[10., 10., 40., 50.]], device=image.device),
                 "scores": torch.tensor([.75], device=image.device),
                 "labels": torch.tensor([1], device=image.device)} for image in images]


class TreeInputs(dict):
    def __init__(self):
        super().__init__(pixels=torch.zeros((1,)))
        self.input_ids = torch.zeros((1, 1), dtype=torch.int64)

    def to(self, device):
        return self


class TreeProcessorFixture:
    def __init__(self):
        self.tokenizer = SimpleNamespace(history=[])
        self.image_processor = SimpleNamespace(size={"shortest_edge": 480})

    def __call__(self, *, images, text, return_tensors):
        self.tokenizer.history.append(images.getpixel((0, 0)))
        return TreeInputs()

    def post_process_grounded_object_detection(self, *args, **kwargs):
        return [{"boxes": torch.tensor([[1., 1., 10., 10.]]), "scores": torch.tensor([.8])}]


class TreeModelFixture(nn.Module):
    def __init__(self, barrier):
        super().__init__()
        self.barrier = barrier

    def forward(self, **kwargs):
        self.barrier.wait(timeout=10)
        return object()


class ParallelModelTests(unittest.TestCase):
    def make_predictor(self):
        return TorchTilePredictor(PresenceFixture().eval(), {"profile": {"threshold": .5}},
                                  PersonFixture().eval(), PersonTrainingProfile(), device="cpu")

    def test_forks_share_weights_and_keep_metadata_separate(self):
        original = self.make_predictor()
        first, second = original.fork_for_inference(), original.fork_for_worker()
        for worker in (first, second):
            self.assertIs(worker.presence_model, original.presence_model)
            self.assertIs(worker.person_model, original.person_model)
            self.assertIs(worker.person_profile, original.person_profile)
            self.assertEqual(worker.device, "cpu")
        first.presence_metadata["profile"]["threshold"] = .9
        self.assertEqual(original.presence_metadata["profile"]["threshold"], .5)
        self.assertEqual(second.presence_metadata["profile"]["threshold"], .5)

    def test_readonly_fork_preserves_outputs_and_bn_without_model_mutators(self):
        predictor = self.make_predictor()
        images = [Image.new("RGB", (320, 320), (index * 20, 30, 60)) for index in range(9)]
        expected = predictor.predict_tiles(images)
        state = {name: value.clone() for name, value in predictor.presence_model.state_dict().items()}
        worker = predictor.fork_for_inference()
        with patch.object(predictor.presence_model, "to", side_effect=AssertionError("move shared weights")), \
                patch.object(predictor.presence_model, "eval", side_effect=AssertionError("mutate shared mode")), \
                patch.object(predictor.person_model, "eval", side_effect=AssertionError("mutate shared mode")):
            self.assertEqual(worker.predict_tiles(images), expected)
            self.assertEqual(worker.predict_condition_tiles(images, TaskCondition("building_present")),
                             [type(row)(presence_scores=row.presence_scores) for row in expected])
            self.assertEqual(worker.predict_condition_tiles(images, TaskCondition("person_count", "gte", 3)),
                             [type(row)(person_count=row.person_count) for row in expected])
        for name, value in predictor.presence_model.state_dict().items():
            self.assertTrue(torch.equal(value, state[name]), name)

    def test_unprepared_training_state_is_rejected_without_mutation(self):
        predictor = self.make_predictor()
        predictor.presence_model.train()
        with self.assertRaisesRegex(ValueError, "evaluation"):
            predictor.fork_for_inference()
        image = Image.new("RGB", (320, 320))
        with self.assertRaisesRegex(ValueError, "evaluation"):
            predict_presence(predictor.presence_model, [image], device="cpu", prepare_model=False)
        predictor.person_model.train()
        with self.assertRaisesRegex(ValueError, "evaluation"):
            predict_person(predictor.person_model, [image], predictor.person_profile,
                           device="cpu", prepare_model=False)
        self.assertTrue(predictor.presence_model.training)
        self.assertTrue(predictor.person_model.training)

    def test_fork_rejects_wrong_device_without_moving_parameters_or_buffers(self):
        predictor = self.make_predictor()
        predictor.device = "meta"
        with patch.object(predictor.presence_model, "to", side_effect=AssertionError("move shared weights")):
            with self.assertRaisesRegex(ValueError, "requested device"):
                predictor.fork_for_inference()
        self.assertEqual(next(predictor.presence_model.parameters()).device.type, "cpu")

    def test_concurrent_tree_contexts_keep_tokenizer_and_diagnostics_separate(self):
        original = object.__new__(TreeCountPredictor)
        original.model = TreeModelFixture(threading.Barrier(2)).eval()
        original.processor = TreeProcessorFixture()
        original.profile = TreeCountProfile()
        original.device = torch.device("cpu")
        original.provenance = {"profile": {"prompt": "a tree."}}
        original.last_detections = [{"prior": True}]
        first, second = original.fork_for_inference(), original.fork_for_worker()
        self.assertIs(first.model, second.model)
        self.assertIs(first.model, original.model)
        self.assertIsNot(first.processor.tokenizer, second.processor.tokenizer)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(first.predict_counts, [Image.new("RGB", (20, 20), "red")]),
                       executor.submit(second.predict_counts, [Image.new("RGB", (20, 20), "blue")])]
            self.assertEqual([future.result(timeout=15) for future in futures], [[1], [1]])
        self.assertEqual(first.processor.tokenizer.history, [(255, 0, 0)])
        self.assertEqual(second.processor.tokenizer.history, [(0, 0, 255)])
        self.assertEqual(original.processor.tokenizer.history, [])
        self.assertEqual(original.last_detections, [{"prior": True}])
        first.last_detections[0]["boxes"][0][0] = 99
        first.provenance["profile"]["prompt"] = "changed"
        self.assertEqual(second.last_detections[0]["boxes"][0][0], 1)
        self.assertEqual(second.provenance["profile"]["prompt"], "a tree.")


if __name__ == "__main__":
    unittest.main()
