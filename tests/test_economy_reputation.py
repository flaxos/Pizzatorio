"""Tests for the economy (machine costs, starting money) and reputation systems."""
from __future__ import annotations

import unittest

from config import (
    ASSEMBLY_TABLE,
    BOT_DOCK,
    CONVEYOR,
    EMPTY,
    FRANCHISE_EXPANSION_BONUS,
    MACHINE_BUILD_COSTS,
    OVEN,
    PROCESSOR,
    REPUTATION_GAIN_ONTIME,
    REPUTATION_LOSS_LATE,
    REPUTATION_STARTING,
    SECOND_LOCATION_REWARD_BONUS,
    STARTING_MONEY,
    TECH_UNLOCK_COSTS,
)
from game import FactorySim
from game.entities import Delivery, Item, Order, Tile


class TestStartingMoney(unittest.TestCase):
    """Players begin with seed capital."""

    def test_sim_starts_with_starting_money(self):
        sim = FactorySim(seed=1)
        self.assertEqual(sim.money, STARTING_MONEY)

    def test_starting_money_positive(self):
        self.assertGreater(STARTING_MONEY, 0)

    def test_starting_money_constant_in_config(self):
        # Sanity: STARTING_MONEY is readable from config
        self.assertIsInstance(STARTING_MONEY, int)


class TestMachineBuildCosts(unittest.TestCase):
    """Placing machines on empty ground deducts money."""

    def _sim(self) -> FactorySim:
        return FactorySim(seed=42)

    def test_machine_build_costs_defined_for_main_tiles(self):
        expected_tiles = {CONVEYOR, PROCESSOR, BOT_DOCK, ASSEMBLY_TABLE}
        for tile in expected_tiles:
            self.assertIn(tile, MACHINE_BUILD_COSTS, f"{tile} should have a build cost")

    def test_machine_build_costs_all_positive(self):
        for tile, cost in MACHINE_BUILD_COSTS.items():
            self.assertGreater(cost, 0, f"{tile} build cost must be positive")

    def test_placing_conveyor_on_empty_deducts_money(self):
        sim = self._sim()
        money_before = sim.money
        # Pick a definitely-empty cell not in the static world
        sim.place_tile(0, 0, CONVEYOR, 0)
        self.assertEqual(sim.money, money_before - MACHINE_BUILD_COSTS[CONVEYOR])
        self.assertEqual(sim.grid[0][0].kind, CONVEYOR)

    def test_placing_processor_on_empty_deducts_correct_cost(self):
        sim = self._sim()
        money_before = sim.money
        sim.place_tile(0, 0, PROCESSOR, 0)
        self.assertEqual(sim.money, money_before - MACHINE_BUILD_COSTS[PROCESSOR])

    def test_placing_assembly_table_on_empty_deducts_correct_cost(self):
        sim = self._sim()
        money_before = sim.money
        sim.place_tile(0, 0, ASSEMBLY_TABLE, 0)
        self.assertEqual(sim.money, money_before - MACHINE_BUILD_COSTS[ASSEMBLY_TABLE])

    def test_replacing_existing_tile_is_free(self):
        """Re-placing a tile on an already-occupied cell costs nothing."""
        sim = self._sim()
        sim.place_tile(0, 0, CONVEYOR, 0)
        money_after_first = sim.money
        # Replace the conveyor with itself at different rotation — no additional charge
        sim.place_tile(0, 0, CONVEYOR, 1)
        self.assertEqual(sim.money, money_after_first)

    def test_replacing_conveyor_with_processor_is_free(self):
        """Upgrading an occupied tile to another type also costs nothing."""
        sim = self._sim()
        sim.place_tile(0, 0, CONVEYOR, 0)
        money_after_conveyor = sim.money
        sim.place_tile(0, 0, PROCESSOR, 0)
        self.assertEqual(sim.money, money_after_conveyor)

    def test_demolishing_tile_does_not_change_money(self):
        """Placing EMPTY (demolish) is free."""
        sim = self._sim()
        sim.place_tile(0, 0, CONVEYOR, 0)
        money_after_build = sim.money
        sim.place_tile(0, 0, EMPTY, 0)
        self.assertEqual(sim.money, money_after_build)

    def test_insufficient_funds_blocks_placement(self):
        """A tile cannot be placed if the player cannot afford it."""
        sim = self._sim()
        sim.money = 0
        sim.place_tile(0, 0, CONVEYOR, 0)
        self.assertEqual(sim.grid[0][0].kind, EMPTY, "conveyor should not be placed with no money")
        self.assertEqual(sim.money, 0)

    def test_exact_budget_allows_placement(self):
        """Player can build if they have exactly the required amount."""
        sim = self._sim()
        cost = MACHINE_BUILD_COSTS[CONVEYOR]
        sim.money = cost
        sim.place_tile(0, 0, CONVEYOR, 0)
        self.assertEqual(sim.grid[0][0].kind, CONVEYOR)
        self.assertEqual(sim.money, 0)

    def test_one_below_budget_blocks_placement(self):
        sim = self._sim()
        cost = MACHINE_BUILD_COSTS[PROCESSOR]
        sim.money = cost - 1
        sim.place_tile(0, 0, PROCESSOR, 0)
        self.assertEqual(sim.grid[0][0].kind, EMPTY)
        self.assertEqual(sim.money, cost - 1)

    def test_source_and_sink_cannot_be_overwritten_regardless_of_money(self):
        sim = self._sim()
        money_before = sim.money
        sim.place_tile(1, 7, CONVEYOR, 0)  # SOURCE location
        sim.place_tile(18, 7, CONVEYOR, 0)  # SINK location
        self.assertEqual(sim.grid[7][1].kind, "source")
        self.assertEqual(sim.grid[7][18].kind, "sink")
        self.assertEqual(sim.money, money_before)  # no charge attempted

    def test_oven_placement_locked_by_tech_regardless_of_funds(self):
        sim = self._sim()
        sim.place_tile(0, 0, OVEN, 0)
        self.assertEqual(sim.grid[0][0].kind, EMPTY, "oven must be locked behind tech")
        self.assertEqual(sim.money, STARTING_MONEY)

    def test_oven_placement_deducts_money_when_unlocked(self):
        sim = self._sim()
        sim.tech_tree["ovens"] = True
        money_before = sim.money
        sim.place_tile(0, 0, OVEN, 0)
        self.assertEqual(sim.grid[0][0].kind, OVEN)
        self.assertEqual(sim.money, money_before - MACHINE_BUILD_COSTS[OVEN])

    def test_bot_dock_placement_deducts_money_when_unlocked(self):
        sim = self._sim()
        sim.tech_tree["bots"] = True
        money_before = sim.money
        sim.place_tile(0, 0, BOT_DOCK, 0)
        self.assertEqual(sim.grid[0][0].kind, BOT_DOCK)
        self.assertEqual(sim.money, money_before - MACHINE_BUILD_COSTS[BOT_DOCK])

    def test_money_survives_serialization_round_trip(self):
        sim = self._sim()
        sim.place_tile(0, 0, CONVEYOR, 0)
        d = sim.to_dict()
        sim2 = FactorySim.from_dict(d)
        self.assertEqual(sim.money, sim2.money)


class TestReputation(unittest.TestCase):
    """Reputation rises for on-time deliveries and falls for late ones."""

    def _sim(self) -> FactorySim:
        return FactorySim(seed=77)

    def test_reputation_starts_at_reputation_starting(self):
        sim = self._sim()
        self.assertAlmostEqual(sim.reputation, REPUTATION_STARTING)

    def test_reputation_starting_constant_in_valid_range(self):
        self.assertGreaterEqual(REPUTATION_STARTING, 0.0)
        self.assertLessEqual(REPUTATION_STARTING, 100.0)

    def test_reputation_increases_on_ontime_delivery(self):
        sim = self._sim()
        rep_before = sim.reputation
        # Delivery that completes within SLA
        sim.deliveries.append(
            Delivery(mode="drone", remaining=0.05, elapsed=1.0, sla=10.0,
                     duration=5.0, recipe_key="margherita", reward=12)
        )
        sim.tick(0.1)
        self.assertGreater(sim.reputation, rep_before)

    def test_reputation_decreases_on_late_delivery(self):
        sim = self._sim()
        rep_before = sim.reputation
        # Delivery that completes late (elapsed > sla)
        sim.deliveries.append(
            Delivery(mode="drone", remaining=0.05, elapsed=15.0, sla=10.0,
                     duration=5.0, recipe_key="margherita", reward=12)
        )
        sim.tick(0.1)
        self.assertLess(sim.reputation, rep_before)

    def test_reputation_gain_equals_config_constant(self):
        sim = self._sim()
        rep_before = sim.reputation
        sim.deliveries.append(
            Delivery(mode="drone", remaining=0.05, elapsed=1.0, sla=10.0,
                     duration=5.0, recipe_key="margherita", reward=12)
        )
        sim.tick(0.1)
        self.assertAlmostEqual(sim.reputation, rep_before + REPUTATION_GAIN_ONTIME, places=5)

    def test_reputation_loss_equals_config_constant(self):
        sim = self._sim()
        rep_before = sim.reputation
        sim.deliveries.append(
            Delivery(mode="drone", remaining=0.05, elapsed=15.0, sla=10.0,
                     duration=5.0, recipe_key="margherita", reward=12)
        )
        sim.tick(0.1)
        self.assertAlmostEqual(sim.reputation, rep_before - REPUTATION_LOSS_LATE, places=5)

    def test_reputation_clamped_at_100(self):
        sim = self._sim()
        sim.reputation = 99.9
        sim.deliveries.append(
            Delivery(mode="drone", remaining=0.05, elapsed=1.0, sla=10.0,
                     duration=5.0, recipe_key="margherita", reward=12)
        )
        sim.tick(0.1)
        self.assertLessEqual(sim.reputation, 100.0)

    def test_reputation_clamped_at_0(self):
        sim = self._sim()
        sim.reputation = 0.1
        sim.deliveries.append(
            Delivery(mode="drone", remaining=0.05, elapsed=15.0, sla=10.0,
                     duration=5.0, recipe_key="margherita", reward=12)
        )
        sim.tick(0.1)
        self.assertGreaterEqual(sim.reputation, 0.0)

    def test_reputation_survives_serialization_round_trip(self):
        sim = self._sim()
        sim.reputation = 73.5
        d = sim.to_dict()
        sim2 = FactorySim.from_dict(d)
        self.assertAlmostEqual(sim2.reputation, 73.5, places=5)

    def test_reputation_defaults_in_legacy_save_without_field(self):
        sim = self._sim()
        d = sim.to_dict()
        d.pop("reputation", None)
        sim2 = FactorySim.from_dict(d)
        self.assertAlmostEqual(sim2.reputation, REPUTATION_STARTING, places=5)


class TestExpansionTechUnlocks(unittest.TestCase):
    """second_location and franchise_system tech effects."""

    def _sim(self) -> FactorySim:
        return FactorySim(seed=55)

    def test_expansion_tech_keys_in_tech_tree(self):
        sim = self._sim()
        self.assertIn("second_location", sim.tech_tree)
        self.assertIn("franchise_system", sim.tech_tree)

    def test_expansion_techs_start_locked(self):
        sim = self._sim()
        self.assertFalse(sim.tech_tree["second_location"])
        self.assertFalse(sim.tech_tree["franchise_system"])

    def test_second_location_unlock_cost_positive(self):
        self.assertGreater(TECH_UNLOCK_COSTS["second_location"], 0)

    def test_franchise_system_unlock_cost_greater_than_second_location(self):
        self.assertGreater(
            TECH_UNLOCK_COSTS["franchise_system"],
            TECH_UNLOCK_COSTS["second_location"],
        )

    def test_second_location_auto_unlocks_at_threshold(self):
        sim = self._sim()
        sim.research_points = TECH_UNLOCK_COSTS["second_location"]
        sim.tick(0.01)
        self.assertTrue(sim.tech_tree["second_location"])

    def test_franchise_system_auto_unlocks_at_threshold(self):
        sim = self._sim()
        sim.research_points = TECH_UNLOCK_COSTS["franchise_system"]
        sim.tick(0.01)
        self.assertTrue(sim.tech_tree["franchise_system"])

    def test_second_location_increases_delivery_reward(self):
        """Reward stored in enqueued delivery is boosted when second_location active."""
        sim = self._sim()
        sim.tech_tree["second_location"] = True
        order = Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12)
        sim._enqueue_delivery(order)
        self.assertGreater(sim.deliveries[-1].reward, 12)
        expected = int(12 * (1.0 + SECOND_LOCATION_REWARD_BONUS))
        self.assertEqual(sim.deliveries[-1].reward, expected)

    def test_second_location_does_not_boost_reward_when_locked(self):
        sim = self._sim()
        # second_location starts False
        order = Order(recipe_key="margherita", remaining_sla=60.0, total_sla=60.0, reward=12)
        sim._enqueue_delivery(order)
        self.assertEqual(sim.deliveries[-1].reward, 12)

    def test_franchise_system_accelerates_expansion(self):
        """With franchise_system, expansion_progress grows faster."""
        from config import EXPANSION_BASE_NEEDED

        sim_base = FactorySim(seed=5)
        sim_franchise = FactorySim(seed=5)
        sim_franchise.tech_tree["franchise_system"] = True

        # Give both identical completed counts to isolate the delivery bonus
        sim_base.completed = 10
        sim_franchise.completed = 10

        progress_before_base = sim_base.expansion_progress
        progress_before_franchise = sim_franchise.expansion_progress

        sim_base.tick(0.1)
        sim_franchise.tick(0.1)

        gain_base = sim_base.expansion_progress - progress_before_base
        gain_franchise = sim_franchise.expansion_progress - progress_before_franchise

        self.assertGreater(gain_franchise, gain_base)

    def test_expansion_tech_keys_survive_round_trip(self):
        sim = self._sim()
        sim.tech_tree["second_location"] = True
        sim.tech_tree["franchise_system"] = True
        d = sim.to_dict()
        sim2 = FactorySim.from_dict(d)
        self.assertTrue(sim2.tech_tree["second_location"])
        self.assertTrue(sim2.tech_tree["franchise_system"])

    def test_expansion_tech_keys_locked_survive_round_trip(self):
        sim = self._sim()
        d = sim.to_dict()
        sim2 = FactorySim.from_dict(d)
        self.assertFalse(sim2.tech_tree["second_location"])
        self.assertFalse(sim2.tech_tree["franchise_system"])


if __name__ == "__main__":
    unittest.main()
