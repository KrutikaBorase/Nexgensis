"""FastBox delivery simulator.

The simulator accepts both input formats supplied with the assignment:
- lists of objects, as used by base_case.json;
- dictionaries keyed by ID, as used by the test cases.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

Point = tuple[float, float]


def _point(value: Any, field_name: str) -> Point:
    """Convert a two-number JSON array into a coordinate tuple."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{field_name} must contain exactly two numbers")
    if not all(isinstance(number, (int, float)) and not isinstance(number, bool) for number in value):
        raise ValueError(f"{field_name} must contain only numbers")
    return float(value[0]), float(value[1])


def _records(value: Any, collection_name: str) -> list[tuple[str, Any]]:
    """Normalize either an ID-keyed object or a list of records."""
    if isinstance(value, dict):
        return list(value.items())
    if isinstance(value, list):
        records = []
        for record in value:
            if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                raise ValueError(f"each {collection_name} record must have a string id")
            records.append((record["id"], record))
        return records
    raise ValueError(f"{collection_name} must be an object or an array")


def _location(record: Any, field_name: str) -> Point:
    """Read a location from either a bare coordinate or a record object."""
    if isinstance(record, dict):
        value = record.get("location")
    else:
        value = record
    return _point(value, field_name)


def load_data(path: Path) -> tuple[dict[str, Point], dict[str, Point], list[dict[str, Any]]]:
    """Read and validate a FastBox JSON input file."""
    try:
        with path.open("r", encoding="utf-8") as input_file:
            data = json.load(input_file)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error

    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    for required in ("warehouses", "agents", "packages"):
        if required not in data:
            raise ValueError(f"input is missing required field: {required}")

    warehouses = {
        identifier: _location(record, f"warehouse {identifier} location")
        for identifier, record in _records(data["warehouses"], "warehouse")
    }
    agents = {
        identifier: _location(record, f"agent {identifier} location")
        for identifier, record in _records(data["agents"], "agent")
    }
    if not agents:
        raise ValueError("input must contain at least one agent")

    packages = data["packages"]
    if not isinstance(packages, list):
        raise ValueError("packages must be an array")
    for package in packages:
        if not isinstance(package, dict):
            raise ValueError("each package must be an object")
        if not isinstance(package.get("id"), str):
            raise ValueError("each package must have a string id")
        warehouse_id = package.get("warehouse", package.get("warehouse_id"))
        if warehouse_id not in warehouses:
            raise ValueError(f"package {package['id']} refers to unknown warehouse {warehouse_id}")
        package["warehouse"] = warehouse_id
        package["destination"] = _point(package.get("destination"), f"package {package['id']} destination")

    return warehouses, agents, packages


def distance(first: Point, second: Point) -> float:
    """Return the straight-line Euclidean distance between two points."""
    return math.hypot(second[0] - first[0], second[1] - first[1])


def simulate(warehouses: dict[str, Point], agents: dict[str, Point], packages: list[dict[str, Any]]) -> dict[str, Any]:
    """Assign and deliver packages, returning the required report."""
    assignments: dict[str, list[dict[str, Any]]] = {agent_id: [] for agent_id in agents}

    # Assignment is based on the agent's original position, as required by the prompt.
    for package in packages:
        warehouse_location = warehouses[package["warehouse"]]
        nearest_agent = min(
            agents,
            key=lambda agent_id: (distance(agents[agent_id], warehouse_location), agent_id),
        )
        assignments[nearest_agent].append(package)

    report: dict[str, Any] = {}
    for agent_id, assigned_packages in assignments.items():
        current_location = agents[agent_id]
        total_distance = 0.0

        # Packages keep their input order so repeated runs produce the same route.
        for package in assigned_packages:
            warehouse_location = warehouses[package["warehouse"]]
            total_distance += distance(current_location, warehouse_location)
            total_distance += distance(warehouse_location, package["destination"])
            current_location = package["destination"]

        package_count = len(assigned_packages)
        report[agent_id] = {
            "packages_delivered": package_count,
            "total_distance": round(total_distance, 2),
            "efficiency": round(total_distance / package_count, 2) if package_count else 0.0,
        }

    delivered_agents = [agent_id for agent_id, details in report.items() if details["packages_delivered"]]
    report["best_agent"] = min(
        delivered_agents,
        key=lambda agent_id: (report[agent_id]["efficiency"], agent_id),
    ) if delivered_agents else None
    return report


def write_report(report: dict[str, Any], path: Path) -> None:
    """Write a readable JSON report."""
    with path.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate one day of FastBox deliveries")
    parser.add_argument("input", nargs="?", type=Path, default=Path("base_case.json"), help="input JSON file")
    parser.add_argument("-o", "--output", type=Path, default=Path("report.json"), help="output report path")
    arguments = parser.parse_args()

    try:
        warehouses, agents, packages = load_data(arguments.input)
        report = simulate(warehouses, agents, packages)
        write_report(report, arguments.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"Report written to {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
