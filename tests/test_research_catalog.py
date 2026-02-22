import json
from pathlib import Path

from research_catalog import DEFAULT_RESEARCH, load_research_catalog


def test_load_research_catalog_defaults_when_missing(tmp_path):
    catalog = load_research_catalog(tmp_path / "missing.json")

    assert set(catalog) == set(DEFAULT_RESEARCH)


def test_load_research_catalog_rejects_missing_prerequisites(tmp_path):
    path = tmp_path / "research.json"
    path.write_text(
        json.dumps(
            {
                "turbo_oven": {
                    "display_name": "Turbo Ovens",
                    "branch": "cooking",
                    "cost": 40,
                    "prerequisites": ["ovens"],
                }
            }
        )
    )

    catalog = load_research_catalog(path)

    assert set(catalog) == set(DEFAULT_RESEARCH)


def test_load_research_catalog_accepts_valid_payload(tmp_path):
    path = tmp_path / "research.json"
    path.write_text(
        json.dumps(
            {
                "starter": {
                    "display_name": "Starter Tech",
                    "branch": "general",
                    "cost": 10,
                    "prerequisites": [],
                },
                "advanced": {
                    "display_name": "Advanced Tech",
                    "branch": "general",
                    "cost": 20,
                    "prerequisites": ["starter"],
                },
            }
        )
    )

    catalog = load_research_catalog(path)

    assert list(catalog) == ["starter", "advanced"]
    assert catalog["advanced"]["prerequisites"] == ["starter"]
