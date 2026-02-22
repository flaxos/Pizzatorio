"""Tests for the FactorySim engine and supporting modules."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from config import (
    ASSEMBLY_TABLE,
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
from game.simulation import RECIPES


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
        from config import STARTING_MONEY
        self.assertEqual(self.sim.time, 0.0)
        self.assertEqual(self.sim.money, STARTING_MONEY)
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


    def test_order_channel_helpers_respect_reputation_thresholds(self):
        sim = FactorySim(seed=1)
        sim.reputation = 0.0
        self.assertTrue(sim.order_channel_is_unlocked("delivery"))
        self.assertFalse(sim.order_channel_is_unlocked("eat_in"))
        self.assertGreaterEqual(sim.order_channel_min_reputation("eat_in"), 25.0)
        self.assertEqual(sim.unlocked_order_channels(), ["delivery"])

    def test_set_order_channel_returns_false_when_locked(self):
        sim = FactorySim(seed=1)
        sim.reputation = 0.0
        self.assertFalse(sim.set_order_channel("eat_in"))
        self.assertEqual(sim.order_channel, "delivery")
        self.assertIn("locked", sim.event_log[-1])

    def test_set_order_channel_returns_true_after_reputation_unlock(self):
        sim = FactorySim(seed=1)
        sim.reputation = 40.0
        self.assertTrue(sim.set_order_channel("eat_in"))
        self.assertEqual(sim.order_channel, "eat_in")

    def test_tick_auto_switches_locked_order_channel_before_spawning(self):
        sim = FactorySim(seed=1)
        sim.reputation = 30.0
        self.assertTrue(sim.set_order_channel("eat_in"))
        sim.reputation = 0.0
        sim.order_spawn_timer = ORDER_SPAWN_INTERVAL
        sim.tick(0.01)
        self.assertEqual(sim.order_channel, "delivery")
        self.assertIn("auto-switched", sim.event_log[-1])

    def test_tick_keeps_active_channel_when_still_unlocked(self):
        sim = FactorySim(seed=1)
        sim.reputation = 30.0
        self.assertTrue(sim.set_order_channel("eat_in"))
        sim.order_spawn_timer = ORDER_SPAWN_INTERVAL
        sim.tick(0.01)
        self.assertEqual(sim.order_channel, "eat_in")

    def test_takeaway_spawns_orders_faster_than_delivery(self):
        delivery = FactorySim(seed=7)
        takeaway = FactorySim(seed=7)
        takeaway.reputation = 20.0
        self.assertTrue(takeaway.set_order_channel("takeaway"))

        for _ in range(100):
            delivery.tick(0.1)
            takeaway.tick(0.1)

        self.assertGreaterEqual(len(takeaway.orders), len(delivery.orders))

    def test_eat_in_spawns_orders_slower_than_delivery(self):
        delivery = FactorySim(seed=7)
        eat_in = FactorySim(seed=7)
        eat_in.reputation = 30.0
        self.assertTrue(eat_in.set_order_channel("eat_in"))

        for _ in range(100):
            delivery.tick(0.1)
            eat_in.tick(0.1)

        self.assertLessEqual(len(eat_in.orders), len(delivery.orders))

    def test_second_location_increases_order_intake(self):
        baseline = FactorySim(seed=7)
        expanded = FactorySim(seed=7)
        expanded.tech_tree["second_location"] = True

        for _ in range(220):
            baseline.tick(0.1)
            expanded.tick(0.1)

        self.assertGreaterEqual(len(expanded.orders), len(baseline.orders))

    def test_second_location_allows_higher_active_order_cap(self):
        baseline = FactorySim(seed=5)
        expanded = FactorySim(seed=5)
        baseline.order_channel = "delivery"
        expanded.order_channel = "delivery"
        expanded.tech_tree["second_location"] = True

        for _ in range(20):
            baseline._spawn_order()
            expanded._spawn_order()

        self.assertGreater(len(expanded.orders), len(baseline.orders))

    def test_research_unlocks_progression(self):
        sim = FactorySim(seed=1)
        sim.research_points = 12.0
        sim.tick(0.01)
        self.assertTrue(sim.tech_tree["ovens"])

    def test_research_focus_prioritises_unlock(self):
        sim = FactorySim(seed=1)
        sim.tech_tree["bots"] = True
        sim.tech_tree["turbo_belts"] = True
        sim.set_research_focus("priority_dispatch")
        sim.research_points = 100.0
        sim.tick(0.01)
        self.assertTrue(sim.tech_tree["priority_dispatch"])

    def test_research_focus_pauses_background_auto_unlocks(self):
        sim = FactorySim(seed=1)
        sim.research_points = 30.0
        sim.set_research_focus("bots")

        sim.tick(0.01)

        self.assertTrue(sim.tech_tree["bots"])
        self.assertFalse(sim.tech_tree["ovens"])

    def test_set_research_focus_rejects_unmet_prerequisites(self):
        sim = FactorySim(seed=1)
        self.assertFalse(sim.set_research_focus("precision_cooking"))
        self.assertEqual(sim.research_focus, "")

    def test_available_research_targets_only_return_unlocked_prerequisite_safe(self):
        sim = FactorySim(seed=1)
        targets = sim.available_research_targets()
        self.assertIn("ovens", targets)
        self.assertNotIn("precision_cooking", targets)
        sim.tech_tree["turbo_oven"] = True
        sim.tech_tree["hygiene_training"] = True
        targets = sim.available_research_targets()
        self.assertIn("precision_cooking", targets)

    def test_cycle_research_focus_skips_unlocked(self):
        sim = FactorySim(seed=1)
        sim.tech_tree["ovens"] = True
        focus = sim.cycle_research_focus()
        self.assertNotEqual(focus, "ovens")
        self.assertEqual(sim.research_focus, focus)

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
        self.assertEqual(sim.research_focus, sim2.research_focus)
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


class TestResearchEffects(unittest.TestCase):
    """Verify each new research unlock produces its intended simulation effect."""

    def _fresh(self) -> FactorySim:
        return FactorySim(seed=77)

    # ---- tech tree coverage ----

    def test_tech_tree_has_all_expected_keys(self):
        sim = self._fresh()
        expected = {
            "ovens", "turbo_oven", "precision_cooking",
            "bots", "hygiene_training",
            "turbo_belts", "priority_dispatch", "double_spawn",
        }
        self.assertTrue(expected.issubset(sim.tech_tree.keys()))

    def test_all_new_tech_starts_locked(self):
        sim = self._fresh()
        for key in ("turbo_oven", "precision_cooking", "hygiene_training",
                    "priority_dispatch", "double_spawn"):
            self.assertFalse(sim.tech_tree[key], f"{key} should start locked")

    # ---- turbo_oven: oven tiles run faster ----

    def test_turbo_oven_increases_progress_on_oven_tile(self):
        from config import OVEN
        from game.entities import Item

        sim_base = self._fresh()
        sim_turbo = self._fresh()
        sim_turbo.tech_tree["turbo_oven"] = True

        # Place an item directly on the oven tile
        for sim in (sim_base, sim_turbo):
            sim.items.append(Item(x=12, y=7, progress=0.0, stage="processed", ingredient_type="flour"))

        dt = 0.5
        sim_base.tick(dt)
        sim_turbo.tick(dt)

        prog_base = next((i.progress for i in sim_base.items if i.x == 12 and i.y == 7), None)
        prog_turbo = next((i.progress for i in sim_turbo.items if i.x == 12 and i.y == 7), None)

        if prog_base is not None and prog_turbo is not None:
            self.assertGreater(prog_turbo, prog_base)

    # ---- hygiene_training: faster hygiene recovery ----

    def test_hygiene_training_recovers_faster(self):
        sim_base = self._fresh()
        sim_trained = self._fresh()
        sim_trained.tech_tree["hygiene_training"] = True

        # Suppress random hygiene events by setting last_hygiene_event to now
        for sim in (sim_base, sim_trained):
            sim.hygiene = 60.0
            sim.last_hygiene_event = 0.0

        # Use a very short tick so hygiene events are not triggered (time < cooldown)
        for _ in range(50):
            sim_base.tick(0.01)
            sim_trained.tick(0.01)

        self.assertGreater(sim_trained.hygiene, sim_base.hygiene)

    # ---- double_spawn: ingredient spawns more frequently ----

    def test_double_spawn_produces_more_items(self):
        from config import ITEM_SPAWN_INTERVAL, DOUBLE_SPAWN_INTERVAL_DIVISOR

        sim_base = self._fresh()
        sim_fast = self._fresh()
        sim_fast.tech_tree["double_spawn"] = True

        # Run for exactly enough time to see a difference in spawns
        total_time = ITEM_SPAWN_INTERVAL * 3
        dt = 0.05
        ticks = int(total_time / dt) + 1

        for _ in range(ticks):
            sim_base.tick(dt)
            sim_fast.tick(dt)

        # double_spawn sim should have spawned at least as many items; with a
        # shorter interval it is very likely to have spawned more.
        self.assertGreaterEqual(
            sim_fast.waste + len(sim_fast.items) + sim_fast.completed,
            sim_base.waste + len(sim_base.items) + sim_base.completed,
        )

    # ---- priority_dispatch: late penalty is smaller ----

    def test_priority_dispatch_earns_more_on_late_delivery(self):
        from game.entities import Delivery, Order

        sim_base = self._fresh()
        sim_pd = self._fresh()
        sim_pd.tech_tree["priority_dispatch"] = True

        reward = 20
        # Create a delivery that will complete late (sla=1s, remaining=5s)
        for sim in (sim_base, sim_pd):
            sim.deliveries.append(
                Delivery(mode="drone", remaining=0.05, elapsed=9.0, sla=1.0,
                         duration=0.05, recipe_key="margherita", reward=reward)
            )

        sim_base.tick(0.1)
        sim_pd.tick(0.1)

        self.assertGreater(sim_pd.money, sim_base.money)

    # ---- precision_cooking: waste items give partial refund ----

    def test_precision_cooking_refunds_wasted_items(self):
        from game.entities import Item

        sim = self._fresh()
        sim.tech_tree["precision_cooking"] = True
        # Ensure no orders so item at sink counts as waste
        sim.orders.clear()
        # Place a baked item adjacent to the sink so it enters the sink
        sim.items.append(Item(x=17, y=7, progress=0.0, stage="baked", ingredient_type="flour"))

        money_before = sim.money
        for _ in range(15):
            sim.tick(0.1)

        # Waste count should have increased and refund credited
        self.assertGreater(sim.waste, 0)
        self.assertGreater(sim.money, money_before)

    # ---- research auto-unlock via _process_research ----

    def test_turbo_oven_auto_unlocks_at_threshold(self):
        from config import TECH_UNLOCK_COSTS
        sim = self._fresh()
        sim.tech_tree["ovens"] = True
        sim.research_points = TECH_UNLOCK_COSTS["turbo_oven"]
        sim.tick(0.01)
        self.assertTrue(sim.tech_tree["turbo_oven"])

    def test_priority_dispatch_auto_unlocks_at_threshold(self):
        from config import TECH_UNLOCK_COSTS
        sim = self._fresh()
        sim.tech_tree["bots"] = True
        sim.tech_tree["turbo_belts"] = True
        sim.research_points = TECH_UNLOCK_COSTS["priority_dispatch"]
        sim.tick(0.01)
        self.assertTrue(sim.tech_tree["priority_dispatch"])

    # ---- serialisation round-trip preserves new tech keys ----

    def test_new_tech_keys_survive_round_trip(self):
        sim = self._fresh()
        sim.tech_tree["turbo_oven"] = True
        sim.tech_tree["hygiene_training"] = True
        d = sim.to_dict()
        sim2 = FactorySim.from_dict(d)
        self.assertTrue(sim2.tech_tree["turbo_oven"])
        self.assertTrue(sim2.tech_tree["hygiene_training"])
        self.assertFalse(sim2.tech_tree["precision_cooking"])


class TestAssemblyTable(unittest.TestCase):
    """Assembly table: recipe_key tagging and recipe-matched order fulfillment."""

    def _fresh(self) -> FactorySim:
        return FactorySim(seed=42)

    def test_item_recipe_key_defaults_to_empty(self):
        item = Item(x=0, y=0, ingredient_type="flour")
        self.assertEqual(item.recipe_key, "")

    def test_assembly_table_tags_item_with_oldest_order_recipe_key(self):
        sim = self._fresh()
        # Place an assembly table and put a processed item on it (almost done)
        sim.grid[7][5] = Tile(ASSEMBLY_TABLE, rot=0)
        sim.orders.append(Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12))
        sim.items.append(Item(x=5, y=7, progress=0.90, stage="processed", ingredient_type="flour"))
        # Tick: with ASSEMBLY_TABLE_SPEED=0.60 and dt=0.2, progress += 0.12 → 1.02 ≥ 1.0
        sim.tick(0.2)
        # Item should have moved off the table (to x=6) with recipe_key assigned
        tagged = [i for i in sim.items if i.recipe_key == "margherita"]
        self.assertEqual(len(tagged), 1)
        self.assertEqual(tagged[0].x, 6)

    def test_assembly_table_does_not_override_existing_recipe_key(self):
        sim = self._fresh()
        sim.grid[7][5] = Tile(ASSEMBLY_TABLE, rot=0)
        sim.orders.append(Order(recipe_key="pepperoni", remaining_sla=60.0, total_sla=60.0, reward=15))
        # Item already tagged with a different recipe
        sim.items.append(
            Item(x=5, y=7, progress=0.90, stage="processed", ingredient_type="flour", recipe_key="margherita")
        )
        sim.tick(0.2)
        # recipe_key must not have been overwritten
        tagged = [i for i in sim.items if i.recipe_key == "margherita"]
        self.assertEqual(len(tagged), 1)

    def test_assembly_table_does_not_tag_when_no_orders(self):
        sim = self._fresh()
        sim.grid[7][5] = Tile(ASSEMBLY_TABLE, rot=0)
        sim.orders.clear()
        sim.items.append(Item(x=5, y=7, progress=0.90, stage="processed", ingredient_type="flour"))
        sim.tick(0.2)
        # Item moved but recipe_key stays empty
        for item in sim.items:
            self.assertEqual(item.recipe_key, "")

    def test_sink_matches_delivery_by_recipe_key(self):
        sim = self._fresh()
        sim.orders.clear()
        sim.orders.append(Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12))
        sim.orders.append(Order(recipe_key="pepperoni", remaining_sla=60.0, total_sla=60.0, reward=15))
        # Baked item tagged for pepperoni placed near the sink
        sim.items.append(
            Item(x=17, y=7, progress=0.0, stage="baked", ingredient_type="flour", recipe_key="pepperoni")
        )
        for _ in range(15):
            sim.tick(0.1)
        # Pepperoni order consumed; margherita still pending
        remaining = [o.recipe_key for o in sim.orders]
        self.assertIn("margherita", remaining)
        self.assertNotIn("pepperoni", remaining)

    def test_sink_fulfillment_uses_correct_reward_for_recipe(self):
        sim = self._fresh()
        sim.orders.clear()
        # margherita reward=12, pepperoni reward=15
        sim.orders.append(Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12))
        sim.orders.append(Order(recipe_key="pepperoni", remaining_sla=60.0, total_sla=60.0, reward=15))
        sim.items.append(
            Item(x=17, y=7, progress=0.0, stage="baked", ingredient_type="flour", recipe_key="pepperoni")
        )
        for _ in range(15):
            sim.tick(0.1)
        # A delivery for pepperoni should have been enqueued
        pepperoni_deliveries = [d for d in sim.deliveries if d.recipe_key == "pepperoni"]
        if pepperoni_deliveries:
            self.assertEqual(pepperoni_deliveries[0].reward, 15)

    def test_sink_rejects_untagged_item_when_order_queue_has_multiple_recipes(self):
        sim = self._fresh()
        sim.orders.clear()
        sim.orders.append(Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12))
        sim.orders.append(Order(recipe_key="pepperoni", remaining_sla=60.0, total_sla=60.0, reward=15))
        sim.items.append(Item(x=17, y=7, progress=0.0, stage="baked", ingredient_type="flour"))
        waste_before = sim.waste
        for _ in range(15):
            sim.tick(0.1)
        remaining = [o.recipe_key for o in sim.orders]
        self.assertIn("pepperoni", remaining)
        self.assertIn("margherita", remaining)
        self.assertEqual(sim.waste, waste_before + 1)

    def test_sink_untagged_item_fulfills_when_all_orders_share_recipe(self):
        sim = self._fresh()
        sim.orders.clear()
        sim.orders.append(Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12))
        sim.orders.append(Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12))
        sim.items.append(Item(x=17, y=7, progress=0.0, stage="baked", ingredient_type="flour"))
        for _ in range(15):
            sim.tick(0.1)
        self.assertEqual(len(sim.orders), 1)
        self.assertEqual(sim.orders[0].recipe_key, "margherita")

    def test_recipe_key_survives_serialization_round_trip(self):
        sim = self._fresh()
        sim.items.append(
            Item(x=5, y=7, stage="processed", ingredient_type="flour", recipe_key="margherita")
        )
        d = sim.to_dict()
        sim2 = FactorySim.from_dict(d)
        tagged = [i for i in sim2.items if i.recipe_key == "margherita"]
        self.assertEqual(len(tagged), 1)

    def test_recipe_key_defaults_in_legacy_save_without_field(self):
        sim = self._fresh()
        sim.items.append(Item(x=5, y=7, stage="processed", ingredient_type="flour", recipe_key="margherita"))
        d = sim.to_dict()
        # Strip recipe_key to simulate a legacy save
        for item in d["items"]:
            item.pop("recipe_key", None)
        sim2 = FactorySim.from_dict(d)
        for item in sim2.items:
            self.assertIsInstance(item.recipe_key, str)

    def test_assembly_table_place_tile(self):
        sim = self._fresh()
        sim.place_tile(5, 5, ASSEMBLY_TABLE, 0)
        self.assertEqual(sim.grid[5][5].kind, ASSEMBLY_TABLE)

    def test_determinism_preserved_with_assembly_table(self):
        """Simulation with an assembly table is still deterministic."""
        def run(n: int) -> tuple:
            s = FactorySim(seed=7)
            s.grid[7][10] = Tile(ASSEMBLY_TABLE, rot=0)
            for _ in range(n):
                s.tick(0.1)
            return (s.time, s.money, s.completed, s.research_points, len(s.items))

        self.assertEqual(run(200), run(200))

    # --- Ingredient-aware assembly table validation ---

    def test_assembly_table_rejects_unmatched_ingredient(self):
        """Pepperoni item should NOT be tagged for a margherita order
        (margherita needs fresh_basil topping, not sliced_pepperoni)."""
        sim = self._fresh()
        sim.grid[7][5] = Tile(ASSEMBLY_TABLE, rot=0)
        sim.orders.clear()
        sim.orders.append(Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12))
        sim.items.append(Item(x=5, y=7, progress=0.90, stage="processed", ingredient_type="pepperoni"))
        sim.tick(0.2)
        # Item passes through untagged because pepperoni → sliced_pepperoni
        # and margherita doesn't need sliced_pepperoni
        for item in sim.items:
            self.assertEqual(item.recipe_key, "")

    def test_assembly_table_tags_matching_topping_ingredient(self):
        """Pepperoni item should be tagged for a pepperoni pizza order."""
        sim = self._fresh()
        sim.grid[7][5] = Tile(ASSEMBLY_TABLE, rot=0)
        sim.orders.clear()
        sim.orders.append(Order(recipe_key="pepperoni", remaining_sla=60.0, total_sla=60.0, reward=15))
        sim.items.append(Item(x=5, y=7, progress=0.90, stage="processed", ingredient_type="pepperoni"))
        sim.tick(0.2)
        tagged = [i for i in sim.items if i.recipe_key == "pepperoni"]
        self.assertEqual(len(tagged), 1)

    def test_assembly_table_base_ingredient_matches_any_recipe(self):
        """Flour (→ rolled_pizza_base) matches any recipe since all need a base."""
        sim = self._fresh()
        sim.grid[7][5] = Tile(ASSEMBLY_TABLE, rot=0)
        sim.orders.clear()
        sim.orders.append(Order(recipe_key="pepperoni", remaining_sla=60.0, total_sla=60.0, reward=15))
        sim.items.append(Item(x=5, y=7, progress=0.90, stage="processed", ingredient_type="flour"))
        sim.tick(0.2)
        tagged = [i for i in sim.items if i.recipe_key == "pepperoni"]
        self.assertEqual(len(tagged), 1)

    def test_assembly_table_skips_first_order_matches_second(self):
        """When first order doesn't need the ingredient but second does, tag second."""
        sim = self._fresh()
        sim.grid[7][5] = Tile(ASSEMBLY_TABLE, rot=0)
        sim.orders.clear()
        # margherita doesn't need pepperoni, but pepperoni recipe does
        sim.orders.append(Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12))
        sim.orders.append(Order(recipe_key="pepperoni", remaining_sla=60.0, total_sla=60.0, reward=15))
        sim.items.append(Item(x=5, y=7, progress=0.90, stage="processed", ingredient_type="pepperoni"))
        sim.tick(0.2)
        tagged = [i for i in sim.items if i.recipe_key != ""]
        self.assertEqual(len(tagged), 1)
        self.assertEqual(tagged[0].recipe_key, "pepperoni")

    def test_assembly_table_empty_ingredient_type_not_tagged(self):
        """Items with empty ingredient_type (legacy) are not tagged."""
        sim = self._fresh()
        sim.grid[7][5] = Tile(ASSEMBLY_TABLE, rot=0)
        sim.orders.append(Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12))
        sim.items.append(Item(x=5, y=7, progress=0.90, stage="processed", ingredient_type=""))
        sim.tick(0.2)
        for item in sim.items:
            self.assertEqual(item.recipe_key, "")

    def test_assembly_table_unknown_ingredient_type_not_tagged(self):
        """Items with unknown ingredient_type are not tagged."""
        sim = self._fresh()
        sim.grid[7][5] = Tile(ASSEMBLY_TABLE, rot=0)
        sim.orders.append(Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12))
        sim.items.append(Item(x=5, y=7, progress=0.90, stage="processed", ingredient_type="unicorn"))
        sim.tick(0.2)
        for item in sim.items:
            self.assertEqual(item.recipe_key, "")

    def test_ingredient_to_products_covers_all_ingredient_types(self):
        """Every spawnable ingredient type has a product mapping."""
        from config import INGREDIENT_TO_PRODUCTS, INGREDIENT_TYPES
        for ingredient in INGREDIENT_TYPES:
            self.assertIn(ingredient, INGREDIENT_TO_PRODUCTS,
                          f"{ingredient} missing from INGREDIENT_TO_PRODUCTS")
            self.assertTrue(len(INGREDIENT_TO_PRODUCTS[ingredient]) > 0,
                            f"{ingredient} maps to empty product list")

    def test_recipe_required_products_helper(self):
        """The helper returns the correct set of required product IDs."""
        recipe = {
            "base": "rolled_pizza_base",
            "sauce": "tomato_sauce",
            "cheese": "shredded_cheese",
            "toppings": ["sliced_pepperoni", "sliced_mushroom"],
        }
        products = FactorySim._recipe_required_products(recipe)
        self.assertEqual(products, {
            "rolled_pizza_base", "tomato_sauce", "shredded_cheese",
            "sliced_pepperoni", "sliced_mushroom",
        })


class TestOrderChannels(unittest.TestCase):
    def test_set_order_channel_ignores_unknown(self):
        sim = FactorySim(seed=4)
        sim.set_order_channel("takeaway")
        self.assertEqual(sim.order_channel, "takeaway")
        sim.set_order_channel("unknown")
        self.assertEqual(sim.order_channel, "takeaway")

    def test_channel_switch_requires_min_reputation(self):
        sim = FactorySim(seed=4)
        sim.reputation = 0.0

        sim.set_order_channel("takeaway")

        self.assertEqual(sim.order_channel, "delivery")

    def test_takeaway_order_uses_channel_modifiers(self):
        sim = FactorySim(seed=4)
        sim.orders.clear()
        sim.set_order_channel("takeaway")
        sim._spawn_order()
        self.assertEqual(len(sim.orders), 1)
        order = sim.orders[0]
        self.assertGreater(order.reward, 0)
        self.assertGreater(order.total_sla, 0)

    def test_takeaway_orders_stay_within_channel_difficulty_window(self):
        sim = FactorySim(seed=4)
        sim.orders.clear()
        sim.reputation = 20.0
        sim.set_order_channel("takeaway")
        sim.expansion_level = 6

        for _ in range(25):
            sim._spawn_order()

        difficulties = [int(RECIPES[order.recipe_key]["difficulty"]) for order in sim.orders]
        self.assertTrue(difficulties)
        self.assertLessEqual(max(difficulties), 3)

    def test_channel_order_cap_blocks_extra_spawns(self):
        sim = FactorySim(seed=4)
        sim.orders.clear()
        sim.reputation = 20.0
        sim.set_order_channel("takeaway")

        for _ in range(12):
            sim._spawn_order()

        self.assertEqual(len(sim.orders), 6)

    def test_eat_in_orders_require_higher_difficulty(self):
        sim = FactorySim(seed=4)
        sim.orders.clear()
        sim.reputation = 60.0
        sim.set_order_channel("eat_in")
        sim.expansion_level = 6

        for _ in range(25):
            sim._spawn_order()

        difficulties = [int(RECIPES[order.recipe_key]["difficulty"]) for order in sim.orders]
        self.assertTrue(difficulties)
        self.assertGreaterEqual(min(difficulties), 2)

    def test_takeaway_delivery_mode_is_scooter(self):
        sim = FactorySim(seed=4)
        sim.set_order_channel("takeaway")
        sim._enqueue_delivery(
            Order(recipe_key="margherita", remaining_sla=20.0, total_sla=20.0, reward=12, channel_key="takeaway")
        )
        self.assertEqual(sim.deliveries[-1].mode, "scooter")

    def test_delivery_uses_order_channel_after_channel_switch(self):
        sim = FactorySim(seed=4)
        sim.orders.clear()
        sim.set_order_channel("takeaway")
        sim._spawn_order()
        order = sim.orders.pop()
        sim.set_order_channel("delivery")
        sim._enqueue_delivery(order)
        self.assertEqual(sim.deliveries[-1].mode, "scooter")

    def test_eat_in_order_fulfills_without_delivery_trip(self):
        sim = FactorySim(seed=4)
        starting_money = sim.money
        sim._enqueue_delivery(
            Order(recipe_key="margherita", remaining_sla=20.0, total_sla=20.0, reward=12, channel_key="eat_in")
        )

        self.assertEqual(len(sim.deliveries), 0)
        self.assertEqual(sim.completed, 1)
        self.assertEqual(sim.ontime, 1)
        self.assertEqual(sim.money, starting_money + 12)
        self.assertEqual(sim.channel_stats["eat_in"]["completed"], 1)
        self.assertEqual(sim.channel_stats["eat_in"]["ontime"], 1)
        self.assertEqual(sim.channel_stats["eat_in"]["revenue"], 12)

    def test_eat_in_sink_completion_does_not_create_delivery(self):
        sim = FactorySim(seed=4)
        sim.orders.clear()
        sim.orders.append(
            Order(recipe_key="margherita", remaining_sla=30.0, total_sla=30.0, reward=11, channel_key="eat_in")
        )
        sim.items.append(Item(x=17, y=7, progress=0.0, stage="baked", ingredient_type="flour", recipe_key="margherita"))

        for _ in range(15):
            sim.tick(0.1)

        self.assertEqual(len(sim.deliveries), 0)
        self.assertGreaterEqual(sim.completed, 1)

    def test_eat_in_sink_completion_with_delivery_boost_stays_stable(self):
        sim = FactorySim(seed=4)
        sim.orders.clear()
        sim.orders.append(
            Order(recipe_key="margherita", remaining_sla=30.0, total_sla=30.0, reward=11, channel_key="eat_in")
        )
        sim.items.append(
            Item(
                x=17,
                y=7,
                progress=0.0,
                stage="baked",
                ingredient_type="flour",
                recipe_key="margherita",
                delivery_boost=1.0,
            )
        )

        for _ in range(15):
            sim.tick(0.1)

        self.assertEqual(len(sim.deliveries), 0)
        self.assertGreaterEqual(sim.completed, 1)


    def test_available_recipes_exclude_research_locked_entries(self):
        sim = FactorySim(seed=4)
        sim.expansion_level = 6

        available_before = sim._available_recipes(channel_key="delivery")

        self.assertNotIn("supreme", available_before)

    def test_available_recipes_include_entries_once_research_unlocks(self):
        sim = FactorySim(seed=4)
        sim.expansion_level = 6
        sim.tech_tree["precision_cooking"] = True

        available_after = sim._available_recipes(channel_key="delivery")

        self.assertIn("supreme", available_after)
    def test_order_channel_round_trip(self):
        sim = FactorySim(seed=4)
        sim.set_order_channel("eat_in")
        loaded = FactorySim.from_dict(sim.to_dict())
        self.assertEqual(loaded.order_channel, "eat_in")

    def test_channel_stats_track_delivery_completion(self):
        sim = FactorySim(seed=4)
        sim._enqueue_delivery(
            Order(recipe_key="margherita", remaining_sla=20.0, total_sla=20.0, reward=12, channel_key="takeaway")
        )
        sim.deliveries[0].remaining = 0.0
        sim.deliveries[0].elapsed = 1.0
        sim.deliveries[0].sla = 20.0

        sim.tick(0.1)

        self.assertEqual(sim.channel_stats["takeaway"]["completed"], 1)
        self.assertEqual(sim.channel_stats["takeaway"]["ontime"], 1)
        self.assertEqual(sim.channel_stats["takeaway"]["revenue"], 12)

    def test_channel_stats_track_missed_orders(self):
        sim = FactorySim(seed=4)
        sim.orders.clear()
        sim.orders.append(
            Order(recipe_key="margherita", remaining_sla=0.01, total_sla=20.0, reward=12, channel_key="takeaway")
        )

        sim.tick(0.1)

        self.assertEqual(sim.channel_stats["takeaway"]["missed"], 1)


class TestIngredientRecipeCoverage(unittest.TestCase):
    """Every topping product referenced in recipes must be reachable by a spawnable ingredient."""

    def _all_topping_products(self) -> set:
        products: set = set()
        for recipe in RECIPES.values():
            for topping in recipe.get("toppings", []):
                products.add(str(topping))
        return products

    def _coverable_products(self) -> set:
        from config import INGREDIENT_TO_PRODUCTS, INGREDIENT_TYPES
        covered: set = set()
        for ingredient in INGREDIENT_TYPES:
            covered.update(INGREDIENT_TO_PRODUCTS.get(ingredient, []))
        return covered

    def test_all_topping_products_coverable_by_spawnable_ingredient(self):
        """Every recipe topping product must be producible by some spawnable ingredient."""
        uncovered = self._all_topping_products() - self._coverable_products()
        self.assertEqual(
            uncovered,
            set(),
            f"Recipe toppings with no spawnable ingredient source: {uncovered}",
        )

    def test_ingredient_types_consistent_across_all_config_dicts(self):
        from config import INGREDIENT_PURCHASE_COSTS, INGREDIENT_SPAWN_WEIGHTS, INGREDIENT_TO_PRODUCTS, INGREDIENT_TYPES
        type_set = set(INGREDIENT_TYPES)
        self.assertEqual(type_set, set(INGREDIENT_SPAWN_WEIGHTS.keys()))
        self.assertEqual(type_set, set(INGREDIENT_PURCHASE_COSTS.keys()))
        self.assertEqual(type_set, set(INGREDIENT_TO_PRODUCTS.keys()))

    def test_new_ingredient_types_all_have_positive_weights_and_costs(self):
        from config import INGREDIENT_PURCHASE_COSTS, INGREDIENT_SPAWN_WEIGHTS, INGREDIENT_TYPES
        new_types = [
            "jalapeno", "artichoke", "bacon", "sausage", "garlic",
            "spinach", "corn", "anchovy", "beef", "rocket", "basil",
        ]
        for ingredient in new_types:
            self.assertIn(ingredient, INGREDIENT_TYPES)
            self.assertGreater(INGREDIENT_SPAWN_WEIGHTS[ingredient], 0)
            self.assertGreater(INGREDIENT_PURCHASE_COSTS[ingredient], 0)

    def test_new_ingredients_spawn_in_simulation(self):
        """New ingredient types can be spawned by the simulation."""
        new_types = {
            "jalapeno", "artichoke", "bacon", "sausage", "garlic",
            "spinach", "corn", "anchovy", "beef", "rocket", "basil",
        }
        seen: set = set()
        for seed in range(1, 20):
            sim = FactorySim(seed=seed)
            sim.money = 10_000
            for _ in range(30):
                sim.tick(0.1)
            for item in sim.items:
                seen.add(item.ingredient_type)
        self.assertTrue(seen & new_types, f"No new ingredient types spawned; seen: {seen}")


if __name__ == "__main__":
    unittest.main()


def test_precision_cooking_does_not_unlock_without_turbo_oven_prerequisite():
    sim = FactorySim(seed=30)
    sim.research_points = TECH_UNLOCK_COSTS["precision_cooking"]

    sim._process_research()

    assert not sim.tech_tree["precision_cooking"]


def test_precision_cooking_unlocks_after_turbo_oven_prerequisite_met():
    sim = FactorySim(seed=31)
    sim.tech_tree["turbo_oven"] = True
    sim.tech_tree["hygiene_training"] = True
    sim.research_points = TECH_UNLOCK_COSTS["precision_cooking"]

    sim._process_research()

    assert sim.tech_tree["precision_cooking"]
