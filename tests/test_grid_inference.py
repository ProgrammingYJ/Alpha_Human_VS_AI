import unittest
from unittest.mock import patch

from PIL import Image

from alpha_captcha.inference import TorchTilePredictor, split_grid_image
from alpha_captcha.tasks import TaskCondition


class GridInferenceTests(unittest.TestCase):
    def test_row_major_uneven_pixels_and_no_filename_input(self):
        image = Image.new("RGB", (10, 11))
        for y in range(11):
            for x in range(10):
                image.putpixel((x, y), (x, y, 0))
        tiles = split_grid_image(image)
        self.assertEqual(len(tiles), 9)
        self.assertEqual(tiles[0].getpixel((0, 0)), (0, 0, 0))
        self.assertEqual(tiles[4].getpixel((0, 0)), (3, 3, 0))
        self.assertEqual(tiles[8].getpixel((3, 3)), (9, 10, 0))
        self.assertEqual(sum(tile.width * tile.height for tile in tiles), 110)
        with self.assertRaises(TypeError):
            split_grid_image("answers_in_filename.jpg")

    def test_real_inference_adapter_contract_uses_pixels_and_condition_only(self):
        scores = [{"tree": .8, "building": .2, "pond": .1} for _ in range(9)]
        people = [{"person_count": n} for n in range(9)]
        predictor = TorchTilePredictor(object(), {"profile": {"threshold": .5}}, object(), object())
        with patch("alpha_captcha.presence_model.predict_presence", return_value=scores) as presence, patch("alpha_captcha.person_model.predict_person", return_value=people) as person:
            result = predictor.solve_grid(Image.new("RGB", (96, 96)), TaskCondition("person_count", "gte", 3))
        self.assertEqual(result["selected_tiles"], [3, 4, 5, 6, 7, 8])
        self.assertFalse(result["mouse_control_performed"])
        self.assertTrue(all(isinstance(image, Image.Image) for image in presence.call_args.args[1]))
        self.assertTrue(all(isinstance(image, Image.Image) for image in person.call_args.args[1]))


if __name__ == "__main__":
    unittest.main()
