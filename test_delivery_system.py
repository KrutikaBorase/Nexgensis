import json
import random
from pathlib import Path

import pytest

from delivery_system import ascii_routes, load_data, simulate, write_top_performer_csv


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


def test_random_delays_are_reproducible_and_do_not_change_distance():
    warehouses, agents, packages = load_data(ROOT / "base_case.json")

    first_report = simulate(warehouses, agents, packages, delay_rng=random.Random(7), max_delay=3)
    second_report = simulate(warehouses, agents, packages, delay_rng=random.Random(7), max_delay=3)
    plain_report = simulate(warehouses, agents, packages)

    assert first_report == second_report
    assert first_report["A1"]["total_distance"] == plain_report["A1"]["total_distance"]
    assert "total_delay" in first_report["A1"]


def test_bonus_route_and_top_performer_csv(tmp_path: Path):
    warehouses, agents, packages = load_data(ROOT / "base_case.json")
    joining_agent = ("A4", (25.0, 25.0))
    report = simulate(warehouses, agents, packages, join_agent=joining_agent, join_after=2)
    route_text = ascii_routes(warehouses, agents, packages, joining_agent, 2)
    csv_path = tmp_path / "top_performer.csv"

    write_top_performer_csv(report, csv_path)

    assert "A4: START (25.0, 25.0)" in route_text
    assert report["best_agent"] in csv_path.read_text(encoding="utf-8")
