from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from order_channel_catalog import DEFAULT_ORDER_CHANNELS, load_order_channel_catalog


class TestOrderChannelCatalog(unittest.TestCase):
    def test_load_defaults_when_missing(self):
        channels = load_order_channel_catalog(Path("/tmp/definitely_missing_order_channels.json"))
        self.assertEqual(set(channels.keys()), set(DEFAULT_ORDER_CHANNELS.keys()))

    def test_load_valid_file(self):
        payload = {
            "delivery": {
                "display_name": "Delivery",
                "reward_multiplier": 1.2,
                "sla_multiplier": 0.9,
                "demand_weight": 2.0,
                "delivery_modes": ["drone"],
            }
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            Path(f.name).write_text(json.dumps(payload))
            path = Path(f.name)

        try:
            channels = load_order_channel_catalog(path)
            self.assertIn("delivery", channels)
            self.assertEqual(channels["delivery"]["delivery_modes"], ["drone"])
            self.assertEqual(channels["delivery"]["reward_multiplier"], 1.2)
        finally:
            path.unlink(missing_ok=True)

    def test_invalid_entries_are_filtered(self):
        payload = {
            "bad": {
                "display_name": "",
                "reward_multiplier": -1,
                "sla_multiplier": 0,
                "demand_weight": 1,
                "delivery_modes": [],
            },
            "good": {
                "display_name": "Good",
                "reward_multiplier": 1,
                "sla_multiplier": 1,
                "demand_weight": 1,
                "delivery_modes": ["scooter"],
            },
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            Path(f.name).write_text(json.dumps(payload))
            path = Path(f.name)

        try:
            channels = load_order_channel_catalog(path)
            self.assertEqual(set(channels.keys()), {"good"})
        finally:
            path.unlink(missing_ok=True)
