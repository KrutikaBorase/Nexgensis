"""FastBox delivery simulator.

The simulator accepts both input formats supplied with the assignment:
- lists of objects, as used by base_case.json;
- dictionaries keyed by ID, as used by the test cases.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
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
    # Dictionary input already carries IDs as keys; list input carries the ID
    # inside each record. Returning the same pair format keeps later code simple.
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
    # The test fixtures use both [x, y] values and objects with a location field.
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

    # Normalize both fixture schemas into one internal representation so the
    # assignment and delivery logic does not need format-specific branches.
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
        # Validate references while loading so simulation never has to handle a
        # missing warehouse or malformed destination halfway through a route.
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
    # hypot is equivalent to sqrt(dx**2 + dy**2) and is numerically robust.
    return math.hypot(second[0] - first[0], second[1] - first[1])


def _assign_packages(
    warehouses: dict[str, Point],
    agents: dict[str, Point],
    packages: list[dict[str, Any]],
    join_agent: tuple[str, Point] | None = None,
    join_after: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Assign packages, optionally adding an agent after a mid-day cutoff."""
    active_agents = dict(agents)
    assignments: dict[str, list[dict[str, Any]]] = {agent_id: [] for agent_id in active_agents}

    for package_number, package in enumerate(packages):
        # A joining agent becomes eligible only for packages not yet assigned.
        if join_agent and join_after is not None and package_number == join_after:
            agent_id, location = join_agent
            active_agents[agent_id] = location
            assignments[agent_id] = []

        warehouse_location = warehouses[package["warehouse"]]
        nearest_agent = min(
            active_agents,
            key=lambda agent_id: (distance(active_agents[agent_id], warehouse_location), agent_id),
        )
        assignments[nearest_agent].append(package)

    return assignments


def simulate(
    warehouses: dict[str, Point],
    agents: dict[str, Point],
    packages: list[dict[str, Any]],
    delay_rng: random.Random | None = None,
    max_delay: float = 0.0,
    join_agent: tuple[str, Point] | None = None,
    join_after: int | None = None,
) -> dict[str, Any]:
    """Assign and deliver packages, returning the required report."""
    if max_delay < 0:
        raise ValueError("max_delay cannot be negative")
    if join_agent and join_agent[0] in agents:
        raise ValueError(f"joining agent already exists: {join_agent[0]}")
    if join_after is not None and not 0 <= join_after <= len(packages):
        raise ValueError("join_after must be between 0 and the package count")
    if join_agent and join_after is None:
        raise ValueError("join_after is required when adding an agent")

    # Assignment is based on each agent's original position. Delivery movement
    # is intentionally excluded so package order cannot change ownership.
    assignments = _assign_packages(warehouses, agents, packages, join_agent, join_after)

    report: dict[str, Any] = {}
    route_agents = dict(agents)
    if join_agent:
        route_agents[join_agent[0]] = join_agent[1]
    for agent_id, assigned_packages in assignments.items():
        current_location = route_agents[agent_id]
        total_distance = 0.0
        total_delay = 0.0

        # Keep input order for a deterministic route. Each package contributes
        # two legs: current position -> warehouse -> destination.
        for package in assigned_packages:
            warehouse_location = warehouses[package["warehouse"]]
            total_distance += distance(current_location, warehouse_location)
            total_distance += distance(warehouse_location, package["destination"])
            current_location = package["destination"]
            if delay_rng is not None:
                total_delay += delay_rng.uniform(0.0, max_delay)

        package_count = len(assigned_packages)
        # Keep the report readable while retaining the full precision above for
        # choosing the most efficient agent.
        report[agent_id] = {
            "packages_delivered": package_count,
            "total_distance": round(total_distance, 2),
            "efficiency": round(total_distance / package_count, 2) if package_count else 0.0,
        }
        if delay_rng is not None:
            report[agent_id]["total_delay"] = round(total_delay, 2)

    # Agents with no deliveries cannot be the best performer for this day.
    delivered_agents = [agent_id for agent_id, details in report.items() if details["packages_delivered"]]
    report["best_agent"] = min(
        delivered_agents,
        key=lambda agent_id: (report[agent_id]["efficiency"], agent_id),
    ) if delivered_agents else None

    delivered_count = sum(details["packages_delivered"] for details in report.values() if isinstance(details, dict))
    if delivered_count != len(packages):
        raise RuntimeError(f"delivery count mismatch: {delivered_count} of {len(packages)} packages delivered")
    return report


def ascii_routes(
    warehouses: dict[str, Point],
    agents: dict[str, Point],
    packages: list[dict[str, Any]],
    join_agent: tuple[str, Point] | None = None,
    join_after: int | None = None,
) -> str:
    """Return a compact ASCII route map for each agent's delivery sequence."""
    assignments = _assign_packages(warehouses, agents, packages, join_agent, join_after)
    route_agents = dict(agents)
    if join_agent:
        route_agents[join_agent[0]] = join_agent[1]
    lines = ["FastBox routes (start -> warehouse -> destination):"]
    for agent_id, assigned_packages in assignments.items():
        route = [f"START {route_agents[agent_id]}"]
        for package in assigned_packages:
            route.extend([package["warehouse"], f"{package['id']} {package['destination']}"])
        lines.append(f"{agent_id}: " + " -> ".join(route))
    return "\n".join(lines)


def write_top_performer_csv(report: dict[str, Any], path: Path) -> None:
    """Export the best agent's report row for spreadsheet-friendly review."""
    best_agent = report.get("best_agent")
    if best_agent is None:
        raise ValueError("cannot export a top performer when no packages were delivered")
    details = report[best_agent]
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=["agent_id", *details.keys()])
        writer.writeheader()
        writer.writerow({"agent_id": best_agent, **details})


def write_report(report: dict[str, Any], path: Path) -> None:
    """Write a readable JSON report."""
    with path.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate one day of FastBox deliveries")
    parser.add_argument("input", nargs="?", type=Path, default=Path("base_case.json"), help="input JSON file")
    parser.add_argument("-o", "--output", type=Path, default=Path("report.json"), help="output report path")
    parser.add_argument("--random-delays", action="store_true", help="add seeded random delivery delays")
    parser.add_argument("--seed", type=int, default=42, help="random seed used with --random-delays")
    parser.add_argument("--max-delay", type=float, default=10.0, help="maximum delay per package")
    parser.add_argument("--join-agent", nargs=3, metavar=("ID", "X", "Y"), help="add an agent during the day")
    parser.add_argument("--join-after", type=int, help="number of packages assigned before the new agent joins")
    parser.add_argument("--ascii-routes", action="store_true", help="print an ASCII route visualization")
    parser.add_argument("--top-csv", type=Path, help="export the best agent to CSV")
    arguments = parser.parse_args()

    try:
        warehouses, agents, packages = load_data(arguments.input)
        join_agent = None
        if arguments.join_agent:
            join_location = tuple(float(value) for value in arguments.join_agent[1:])
            join_agent = (arguments.join_agent[0], _point(join_location, "joining agent location"))
        delay_rng = random.Random(arguments.seed) if arguments.random_delays else None
        report = simulate(
            warehouses,
            agents,
            packages,
            delay_rng=delay_rng,
            max_delay=arguments.max_delay,
            join_agent=join_agent,
            join_after=arguments.join_after,
        )
        write_report(report, arguments.output)
        if arguments.ascii_routes:
            print(ascii_routes(warehouses, agents, packages, join_agent, arguments.join_after))
        if arguments.top_csv:
            write_top_performer_csv(report, arguments.top_csv)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"Report written to {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
