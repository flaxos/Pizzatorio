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


if __name__ == "__main__":
    unittest.main()
