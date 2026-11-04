import unittest

from alpha_captcha.tree_model import TreeCountProfile, TreeCountPredictor


class TreeProfileTests(unittest.TestCase):
    def test_rejects_invalid_limits_and_different_target(self):
        for options in ({"box_threshold": True}, {"text_threshold": 0}, {"nms_iou": float("nan")}, {"shortest_edge": 800}, {"prompt": "a person."}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                TreeCountProfile(**options)

    def test_count_comparison_uses_actual_predicted_instances(self):
        predictor = object.__new__(TreeCountPredictor)
        predictor.predict_counts = lambda images: [0, 2, 3, 5]
        self.assertEqual(predictor.predict_at_least_three([object()] * 4), [False, False, True, True])


if __name__ == "__main__":
    unittest.main()
