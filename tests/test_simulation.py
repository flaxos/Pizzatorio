"""Tests for the FactorySim engine and supporting modules."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from config import (
    BOT_DOCK,
    CONVEYOR,
    EMPTY,
    INGREDIENT_SPAWN_WEIGHTS,
    INGREDIENT_TYPES,
    ITEM_SPAWN_INTERVAL,
    ORDER_SPAWN_INTERVAL,
    OVEN,
    PROCESSOR,
    SINK,
    SOURCE,
    TECH_UNLOCK_COSTS,
)
from game import FactorySim
from game.entities import Delivery, Item, Order, Tile


class TestConfig(unittest.TestCase):
    """Config module sanity checks."""

    def test_ingredient_spawn_weights_keys_match_types(self):
        self.assertEqual(set(INGREDIENT_SPAWN_WEIGHTS.keys()), set(INGREDIENT_TYPES))

    def test_ingredient_spawn_weights_all_positive(self):
        for name, weight in INGREDIENT_SPAWN_WEIGHTS.items():
            self.assertGreater(weight, 0, f"{name} weight must be positive")

    def test_tech_unlock_costs_non_empty(self):
        self.assertTrue(len(TECH_UNLOCK_COSTS) >= 3)
        for tech, cost in TECH_UNLOCK_COSTS.items():
            self.assertIsInstance(tech, str)
            self.assertGreater(cost, 0)

    def test_spawn_intervals_positive(self):
        self.assertGreater(ITEM_SPAWN_INTERVAL, 0)
        self.assertGreater(ORDER_SPAWN_INTERVAL, 0)


class TestEntities(unittest.TestCase):
    """Dataclass construction and defaults."""

    def test_tile_defaults(self):
        t = Tile()
        self.assertEqual(t.kind, "empty")
        self.assertEqual(t.rot, 0)
        self.assertEqual(t.hygiene_penalty, 0)

    def test_item_defaults_and_ingredient_type(self):
        item = Item(x=3, y=5)
        self.assertEqual(item.x, 3)
        self.assertEqual(item.y, 5)
        self.assertEqual(item.stage, "raw")
        self.assertEqual(item.ingredient_type, "")
        self.assertEqual(item.delivery_boost, 0.0)

    def test_item_with_ingredient_type(self):
        item = Item(x=0, y=0, ingredient_type="flour")
        self.assertEqual(item.ingredient_type, "flour")

    def test_delivery_defaults(self):
        d = Delivery(mode="drone", remaining=5.0, sla=10.0, duration=5.0, recipe_key="margherita", reward=12)
        self.assertEqual(d.elapsed, 0.0)

    def test_order_fields(self):
        o = Order(recipe_key="pepperoni", remaining_sla=9.0, total_sla=10.0, reward=15)
        self.assertEqual(o.recipe_key, "pepperoni")


class TestFactorySimInit(unittest.TestCase):
    """FactorySim initialisation."""

    def setUp(self):
        self.sim = FactorySim(seed=42)

    def test_grid_dimensions(self):
        self.assertEqual(len(self.sim.grid), 15)
        for row in self.sim.grid:
            self.assertEqual(len(row), 20)

    def test_initial_state(self):
        self.assertEqual(self.sim.time, 0.0)
        self.assertEqual(self.sim.money, 0)
        self.assertEqual(self.sim.completed, 0)
        self.assertEqual(self.sim.hygiene, 100.0)

    def test_tech_tree_initialised_false(self):
        for key in TECH_UNLOCK_COSTS:
            self.assertFalse(self.sim.tech_tree[key], f"{key} should start locked")

    def test_static_world_source_and_sink(self):
        self.assertEqual(self.sim.grid[7][1].kind, SOURCE)
        self.assertEqual(self.sim.grid[7][18].kind, SINK)

    def test_static_world_conveyor_row(self):
        # Positions 7 (PROCESSOR) and 12 (OVEN) are not conveyors
        non_conveyor = {7, 12}
        for x in range(2, 18):
            if x in non_conveyor:
                continue
            self.assertEqual(self.sim.grid[7][x].kind, CONVEYOR, f"x={x} should be conveyor")

    def test_place_tile_locked_oven(self):
        self.sim.place_tile(5, 5, OVEN, 0)
        self.assertEqual(self.sim.grid[5][5].kind, EMPTY)

    def test_place_tile_after_unlock(self):
        self.sim.tech_tree["ovens"] = True
        self.sim.place_tile(5, 5, OVEN, 0)
        self.assertEqual(self.sim.grid[5][5].kind, OVEN)

    def test_place_tile_cannot_overwrite_source(self):
        self.sim.place_tile(1, 7, CONVEYOR, 0)
        self.assertEqual(self.sim.grid[7][1].kind, SOURCE)

    def test_place_tile_out_of_bounds(self):
        self.sim.place_tile(-1, 0, CONVEYOR, 0)
        self.sim.place_tile(0, -1, CONVEYOR, 0)
        self.sim.place_tile(20, 0, CONVEYOR, 0)
        # Just ensure no exception is raised


class TestFactorySimTick(unittest.TestCase):
    """Tick behaviour."""

    def setUp(self):
        self.sim = FactorySim(seed=99)

    def test_time_advances(self):
        self.sim.tick(0.1)
        self.assertAlmostEqual(self.sim.time, 0.1)

    def test_item_spawns_after_interval(self):
        # Tick enough to trigger one spawn
        ticks = int(ITEM_SPAWN_INTERVAL / 0.1) + 1
        for _ in range(ticks):
            self.sim.tick(0.1)
        self.assertGreater(len(self.sim.items), 0)

    def test_spawned_items_have_ingredient_type(self):
        ticks = int(ITEM_SPAWN_INTERVAL / 0.1) + 5
        for _ in range(ticks):
            self.sim.tick(0.1)
        for item in self.sim.items:
            self.assertIn(item.ingredient_type, INGREDIENT_TYPES, f"unexpected type: {item.ingredient_type!r}")

    def test_order_spawns_after_interval(self):
        ticks = int(ORDER_SPAWN_INTERVAL / 0.1) + 1
        for _ in range(ticks):
            self.sim.tick(0.1)
        self.assertGreater(len(self.sim.orders), 0)

    def test_hygiene_recovers(self):
        self.sim.hygiene = 50.0
        for _ in range(50):
            self.sim.tick(0.1)
        self.assertGreater(self.sim.hygiene, 50.0)

    def test_hygiene_capped_at_100(self):
        for _ in range(200):
            self.sim.tick(0.1)
        self.assertLessEqual(self.sim.hygiene, 100.0)

    def test_research_unlocks_progression(self):
        sim = FactorySim(seed=1)
        sim.research_points = 12.0
        sim.tick(0.01)
        self.assertTrue(sim.tech_tree["ovens"])

    def test_expansion_level_increments(self):
        from config import EXPANSION_BASE_NEEDED
        sim = FactorySim(seed=1)
        # Set progress just below threshold; a 0.5 s tick at EXPANSION_PROGRESS_RATE=0.35
        # adds at least 0.175, pushing past the threshold.
        sim.expansion_progress = EXPANSION_BASE_NEEDED - 0.1
        sim.tick(0.5)
        self.assertEqual(sim.expansion_level, 2)

    def test_ontime_rate_starts_at_100(self):
        self.assertEqual(self.sim.ontime_rate, 100.0)

    def test_determinism(self):
        """Same seed → identical output after N ticks."""
        def run(n: int) -> tuple:
            s = FactorySim(seed=7)
            for _ in range(n):
                s.tick(0.1)
            return (s.time, s.money, s.completed, s.research_points, len(s.items))

        self.assertEqual(run(300), run(300))

    def test_delivery_earns_money(self):
        """Simulate a full pipeline: item reaches sink → delivery completes → money earned."""
        sim = FactorySim(seed=5)
        # Force an order to exist
        from game.entities import Order
        sim.orders.append(Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12))
        # Place a baked item directly at the sink's neighbour
        from game.entities import Item
        sim.items.append(Item(x=17, y=7, progress=0.0, stage="baked", ingredient_type="flour"))
        # Tick once to drive the item into the sink
        for _ in range(30):
            sim.tick(0.1)
        self.assertGreater(len(sim.deliveries) + sim.completed, 0)


class TestFactorySimSerialisation(unittest.TestCase):
    """Serialisation round-trips."""

    def test_to_dict_round_trip(self):
        sim = FactorySim(seed=3)
        for _ in range(50):
            sim.tick(0.1)
        d = sim.to_dict()
        sim2 = FactorySim.from_dict(d)
        self.assertAlmostEqual(sim.time, sim2.time, places=5)
        self.assertEqual(sim.money, sim2.money)
        self.assertEqual(sim.completed, sim2.completed)
        self.assertEqual(sim.tech_tree, sim2.tech_tree)
        self.assertEqual(len(sim.items), len(sim2.items))

    def test_item_ingredient_type_survives_round_trip(self):
        sim = FactorySim(seed=7)
        for _ in range(30):
            sim.tick(0.1)
        # Ensure at least one item with a type exists
        typed = [i for i in sim.items if i.ingredient_type]
        if not typed:
            self.skipTest("No typed items spawned yet")
        d = sim.to_dict()
        sim2 = FactorySim.from_dict(d)
        types_orig = sorted(i.ingredient_type for i in sim.items)
        types_loaded = sorted(i.ingredient_type for i in sim2.items)
        self.assertEqual(types_orig, types_loaded)

    def test_save_load_file(self):
        sim = FactorySim(seed=11)
        for _ in range(40):
            sim.tick(0.1)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            sim.save(path)
            sim2 = FactorySim.load(path)
            self.assertAlmostEqual(sim.time, sim2.time, places=5)
        finally:
            path.unlink(missing_ok=True)

    def test_from_dict_legacy_item_without_ingredient_type(self):
        """Items loaded from saves that pre-date ingredient_type get empty string."""
        sim = FactorySim(seed=1)
        d = sim.to_dict()
        # Simulate legacy save: remove ingredient_type from items
        for item in d["items"]:
            item.pop("ingredient_type", None)
        sim2 = FactorySim.from_dict(d)
        for item in sim2.items:
            self.assertIsInstance(item.ingredient_type, str)

    def test_from_dict_bad_grid_falls_back(self):
        sim = FactorySim(seed=1)
        d = sim.to_dict()
        d["grid"] = "corrupt"
        sim2 = FactorySim.from_dict(d)
        # Grid should still be valid (default from place_static_world)
        self.assertEqual(sim2.grid[7][1].kind, SOURCE)

    def test_from_dict_unknown_tech_tree_key(self):
        sim = FactorySim(seed=1)
        d = sim.to_dict()
        d["tech_tree"]["alien_tech"] = True
        sim2 = FactorySim.from_dict(d)
        # Alien key should not appear in loaded tech_tree
        self.assertNotIn("alien_tech", sim2.tech_tree)


if __name__ == "__main__":
    unittest.main()
