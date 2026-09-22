import json
from pathlib import Path

import pytest

from delivery_system import load_data, simulate


ROOT = Path(__file__).parent
FIXTURES = [ROOT / "base_case.json", *sorted((ROOT / "Python Assignment(Delivery System Test Cases)").glob("*.json"))]


def report_for(path: Path) -> dict:
    warehouses, agents, packages = load_data(path)
    return simulate(warehouses, agents, packages)


def test_base_case_assigns_packages_to_expected_agents():
    report = report_for(ROOT / "base_case.json")

    assert report["A1"]["packages_delivered"] == 2
    assert report["A2"]["packages_delivered"] == 2
    assert report["A3"]["packages_delivered"] == 1
    assert sum(report[agent]["packages_delivered"] for agent in ("A1", "A2", "A3")) == 5
    assert report["best_agent"] in {"A1", "A2", "A3"}


@pytest.mark.parametrize("fixture", FIXTURES)
def test_every_supplied_fixture_delivers_every_package(fixture: Path):
    with fixture.open(encoding="utf-8") as input_file:
        package_count = len(json.load(input_file)["packages"])

    report = report_for(fixture)
    delivered_count = sum(
        details["packages_delivered"]
        for agent_id, details in report.items()
        if agent_id != "best_agent"
    )

    assert delivered_count == package_count
    assert all(details["total_distance"] >= 0 for agent_id, details in report.items() if agent_id != "best_agent")


def test_missing_warehouse_is_rejected(tmp_path: Path):
    invalid_input = tmp_path / "invalid.json"
    invalid_input.write_text(
        json.dumps({
            "warehouses": {"W1": [0, 0]},
            "agents": {"A1": [0, 0]},
            "packages": [{"id": "P1", "warehouse": "W9", "destination": [1, 1]}],
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown warehouse"):
        load_data(invalid_input)
