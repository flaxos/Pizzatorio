import json
import tempfile
import unittest
from pathlib import Path

from recipe_catalog import load_recipe_catalog


class RecipeCatalogTests(unittest.TestCase):
    def test_repository_recipe_catalog_has_expected_scale_and_progression(self):
        catalog = load_recipe_catalog(Path("data/recipes.json"))

        self.assertGreaterEqual(len(catalog), 20)
        tiers = {recipe["unlock_tier"] for recipe in catalog.values()}
        self.assertTrue({0, 1, 2, 3, 4, 5}.issubset(tiers))

        for recipe in catalog.values():
            self.assertLessEqual(len(recipe["toppings"]), 5)
            self.assertGreaterEqual(recipe["difficulty"], 1)

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

    def test_normalizes_cook_temp_and_rejects_blank_display_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "recipes.json"
            path.write_text(
                json.dumps(
                    {
                        "normalized_temp": {
                            "display_name": "Normalized Temp",
                            "sell_price": 11,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": " HIGH ",
                            "difficulty": 1,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                        "blank_name": {
                            "display_name": "   ",
                            "sell_price": 11,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "medium",
                            "difficulty": 1,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                    }
                )
            )
            catalog = load_recipe_catalog(path)

        self.assertIn("normalized_temp", catalog)
        self.assertEqual("high", catalog["normalized_temp"]["cook_temp"])
        self.assertNotIn("blank_name", catalog)

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

    def test_rejects_boolean_numeric_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "recipes.json"
            path.write_text(
                json.dumps(
                    {
                        "bool_sla": {
                            "display_name": "Boolean SLA",
                            "sell_price": 10,
                            "sla": True,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "medium",
                            "difficulty": 1,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                        "bool_cook_time": {
                            "display_name": "Boolean Cook Time",
                            "sell_price": 10,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": True,
                            "cook_temp": "medium",
                            "difficulty": 1,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                    }
                )
            )
            catalog = load_recipe_catalog(path)

        self.assertIn("margherita", catalog)
        self.assertNotIn("bool_sla", catalog)
        self.assertNotIn("bool_cook_time", catalog)

    def test_rejects_invalid_recipe_keys_and_sell_price_types(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "recipes.json"
            path.write_text(
                json.dumps(
                    {
                        "bad-key": {
                            "display_name": "Bad Key",
                            "sell_price": 10,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "medium",
                            "difficulty": 1,
                            "toppings": ["fresh_basil"],
                            "post_oven": [],
                        },
                        "fractional_price": {
                            "display_name": "Fractional Price",
                            "sell_price": 10.5,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "medium",
                            "difficulty": 1,
                            "toppings": ["fresh_basil"],
                            "post_oven": [],
                        },
                    }
                )
            )
            catalog = load_recipe_catalog(path)

        self.assertIn("margherita", catalog)
        self.assertNotIn("bad-key", catalog)
        self.assertNotIn("fractional_price", catalog)

    def test_rejects_invalid_ingredient_ids_and_topping_constraints(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "recipes.json"
            path.write_text(
                json.dumps(
                    {
                        "bad_identifier": {
                            "display_name": "Bad Identifier",
                            "sell_price": 10,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "medium",
                            "difficulty": 1,
                            "base": "rolled-pizza-base",
                            "toppings": ["fresh_basil"],
                            "post_oven": [],
                        },
                        "duplicate_toppings": {
                            "display_name": "Duplicate Toppings",
                            "sell_price": 10,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "medium",
                            "difficulty": 1,
                            "toppings": ["fresh_basil", "fresh_basil"],
                            "post_oven": [],
                        },
                        "too_many_toppings": {
                            "display_name": "Too Many Toppings",
                            "sell_price": 10,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "medium",
                            "difficulty": 1,
                            "toppings": ["a", "b", "c", "d", "e", "f"],
                            "post_oven": [],
                        },
                        "shared_topping_post_oven": {
                            "display_name": "Shared Ingredient",
                            "sell_price": 10,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "medium",
                            "difficulty": 1,
                            "toppings": ["fresh_basil"],
                            "post_oven": ["fresh_basil"],
                        },
                    }
                )
            )
            catalog = load_recipe_catalog(path)

        self.assertIn("margherita", catalog)
        self.assertNotIn("bad_identifier", catalog)
        self.assertNotIn("duplicate_toppings", catalog)
        self.assertNotIn("too_many_toppings", catalog)
        self.assertNotIn("shared_topping_post_oven", catalog)

    def test_catalog_order_is_deterministic_by_tier_then_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "recipes.json"
            path.write_text(
                json.dumps(
                    {
                        "z_tier_zero": {
                            "display_name": "Z Zero",
                            "sell_price": 11,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "low",
                            "difficulty": 1,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                        "a_tier_one": {
                            "display_name": "A One",
                            "sell_price": 11,
                            "sla": 5,
                            "unlock_tier": 1,
                            "cook_time": 8,
                            "cook_temp": "low",
                            "difficulty": 1,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                        "a_tier_zero": {
                            "display_name": "A Zero",
                            "sell_price": 11,
                            "sla": 5,
                            "unlock_tier": 0,
                            "cook_time": 8,
                            "cook_temp": "low",
                            "difficulty": 1,
                            "toppings": ["a"],
                            "post_oven": [],
                        },
                    }
                )
            )
            catalog = load_recipe_catalog(path)

        self.assertEqual(["a_tier_zero", "z_tier_zero", "a_tier_one"], list(catalog.keys()))


if __name__ == "__main__":
    unittest.main()
