import unittest

from alpha_captcha.tasks import TaskCondition, TilePrediction, select_tiles


class TaskTests(unittest.TestCase):
    def test_person_boundaries_for_confirmed_n_range(self):
        predictions = [TilePrediction(person_count=n) for n in [0, 1, 2, 3, 4, 5, 6, 2, 0]]
        self.assertEqual(select_tiles(predictions, TaskCondition("person_present")), [1, 2, 3, 4, 5, 6, 7])
        for n in range(2, 6):
            self.assertEqual(
                select_tiles(predictions, TaskCondition("person_count", "eq", n)),
                [i for i, p in enumerate(predictions) if p.person_count == n],
            )
            self.assertEqual(
                select_tiles(predictions, TaskCondition("person_count", "gte", n)),
                [i for i, p in enumerate(predictions) if p.person_count >= n],
            )

    def test_independent_presence_and_empty_selection(self):
        predictions = [TilePrediction({"tree": .8, "building": .7, "pond": .1}) for _ in range(9)]
        self.assertEqual(select_tiles(predictions, TaskCondition("tree_present"), {"tree": .8}), list(range(9)))
        self.assertEqual(select_tiles(predictions, TaskCondition("building_present"), {"building": .6}), list(range(9)))
        self.assertEqual(select_tiles(predictions, TaskCondition("pond_present"), {"pond": .5}), [])

    def test_unknown_is_not_a_negative(self):
        predictions = [TilePrediction(person_count=0) for _ in range(8)] + [TilePrediction()]
        with self.assertRaisesRegex(ValueError, "unknown"):
            select_tiles(predictions, TaskCondition("person_present"))
        with self.assertRaisesRegex(ValueError, "unknown"):
            select_tiles([TilePrediction() for _ in range(9)], TaskCondition("tree_present"), {"tree": .5})

    def test_private_answer_fields_and_invalid_conditions_rejected(self):
        with self.assertRaisesRegex(ValueError, "public"):
            TaskCondition.from_dict({"task_type": "person_present", "answer_tiles": [1]})
        for kwargs in [dict(n=True, operator="gte"), dict(n=0, operator="eq"), dict(n=2), dict(n=2, operator="gt")]:
            with self.assertRaises(ValueError):
                TaskCondition("person_count", **kwargs)
        for score in [True, float("nan"), float("inf"), -1, 1.1]:
            with self.assertRaises(ValueError):
                TilePrediction({"tree": score})
        with self.assertRaises(ValueError):
            select_tiles([], TaskCondition("person_present"))
        with self.assertRaisesRegex(ValueError, "threshold"):
            select_tiles([TilePrediction({"tree": .8}) for _ in range(9)], TaskCondition("tree_present"))


if __name__ == "__main__":
    unittest.main()
