from __future__ import annotations

import json

from commercial_catalog import DEFAULT_COMMERCIALS, load_commercial_catalog
from game import FactorySim


def test_load_commercial_catalog_defaults_when_missing(tmp_path):
    catalog = load_commercial_catalog(tmp_path / "missing.json")
    assert set(catalog) == set(DEFAULT_COMMERCIALS)


def test_invalid_entries_fall_back_to_defaults(tmp_path):
    path = tmp_path / "commercials.json"
    path.write_text(json.dumps({"campaigns": {"display_name": "", "activation_cost": -1}}))
    catalog = load_commercial_catalog(path)
    assert set(catalog) == set(DEFAULT_COMMERCIALS)


def test_switching_commercial_strategy_charges_activation_cost_once():
    sim = FactorySim(seed=5)
    baseline = sim.money
    promos_cost = int(simulation_commercials()["promos"]["activation_cost"])

    assert sim.set_commercial_strategy("promos")
    assert sim.money == baseline - promos_cost

    # Re-applying same strategy should not charge again.
    assert sim.set_commercial_strategy("promos")
    assert sim.money == baseline - promos_cost


def test_switching_strategy_requires_funds():
    sim = FactorySim(seed=5)
    sim.money = 0
    assert not sim.set_commercial_strategy("franchise")
    assert sim.commercial_strategy != "franchise"


def simulation_commercials():
    from game.simulation import COMMERCIALS

    return COMMERCIALS
