import json
import tempfile
import unittest
from pathlib import Path

from recipe_catalog import load_recipe_catalog


class RecipeCatalogTests(unittest.TestCase):
    def test_loads_defaults_when_file_missing(self):
        catalog = load_recipe_catalog(Path("does_not_exist.json"))
        self.assertIn("margherita", catalog)
        self.assertIn("toppings", catalog["margherita"])
        self.assertIn("cook_time", catalog["margherita"])
        self.assertEqual("medium", catalog["margherita"]["cook_temp"])

    def test_filters_invalid_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "recipes.json"
            path.write_text(
                json.dumps(
                    {
                        "valid": {
                            "display_name": "Valid",
                            "sell_price": 10,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "medium",
                            "difficulty": 1,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                        "invalid": {
                            "display_name": "Invalid",
                            "sell_price": -1,
                            "sla": 5,
                            "unlock_tier": 0,
                        },
                    }
                )
            )
            catalog = load_recipe_catalog(path)

        self.assertIn("valid", catalog)
        self.assertNotIn("invalid", catalog)

    def test_filters_invalid_cook_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "recipes.json"
            path.write_text(
                json.dumps(
                    {
                        "bad_temp": {
                            "display_name": "Bad Temp",
                            "sell_price": 10,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "volcano",
                            "difficulty": 1,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                        "bad_time": {
                            "display_name": "Bad Time",
                            "sell_price": 10,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 0,
                            "cook_temp": "low",
                            "difficulty": 1,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                    }
                )
            )
            catalog = load_recipe_catalog(path)

        self.assertIn("margherita", catalog)
        self.assertNotIn("bad_temp", catalog)
        self.assertNotIn("bad_time", catalog)

    def test_rejects_non_integral_tier_and_difficulty_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "recipes.json"
            path.write_text(
                json.dumps(
                    {
                        "fractional_tier": {
                            "display_name": "Fractional Tier",
                            "sell_price": 10,
                            "sla": 5,
                            "unlock_tier": 1.5,
                            "cook_time": 8,
                            "cook_temp": "medium",
                            "difficulty": 1,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                        "negative_tier": {
                            "display_name": "Negative Tier",
                            "sell_price": 10,
                            "sla": 5,
                            "unlock_tier": -1,
                            "cook_time": 8,
                            "cook_temp": "medium",
                            "difficulty": 1,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                        "fractional_difficulty": {
                            "display_name": "Fractional Difficulty",
                            "sell_price": 10,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "low",
                            "difficulty": 2.5,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                    }
                )
            )
            catalog = load_recipe_catalog(path)

        self.assertIn("margherita", catalog)
        self.assertNotIn("fractional_tier", catalog)
        self.assertNotIn("negative_tier", catalog)
        self.assertNotIn("fractional_difficulty", catalog)


if __name__ == "__main__":
    unittest.main()
