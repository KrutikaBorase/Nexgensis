# FastBox Mystery Delivery System

A small, dependency-free Python simulator for the FastBox logistics assignment.
It reads warehouse, agent, and package data from JSON, assigns each package to
its nearest agent, simulates delivery, and writes `report.json`.

## Run it

```powershell
python delivery_system.py
python delivery_system.py "Python Assignment(Delivery System Test Cases)\test_case_1.json" -o test_case_1_report.json
```

The default input is `base_case.json` and the default output is `report.json`.

## Optional bonus features

The required default run stays deterministic and produces the original report
shape. The following optional flags enable the bonus features:

```powershell
python delivery_system.py base_case.json --random-delays --seed 7 --max-delay 3
python delivery_system.py base_case.json --ascii-routes
python delivery_system.py base_case.json --join-agent A4 25 25 --join-after 2
python delivery_system.py base_case.json --top-csv top_performer.csv
```

Random delays use the supplied seed for reproducible results and are reported
separately as `total_delay`; they do not change physical distance or efficiency.
`--join-after N` makes the new agent eligible for packages beginning at package
index `N`, while earlier packages remain assigned to the original agents.
The ASCII visualization lists each agent's start, warehouse stops, and package
destinations. The CSV export contains the best agent's report row.

## Delivery rules

- Both supplied input shapes are supported: ID-keyed dictionaries and lists of records.
- A package is assigned using Euclidean distance from each agent's initial location to the package warehouse.
- Ties are resolved by agent ID so results are repeatable.
- Each agent delivers assigned packages in their input order. For every package, the route is the agent's current position to the warehouse, then from the warehouse to the destination.
- `efficiency` is total distance divided by packages delivered. Agents with no packages have efficiency `0.0`.
- The best agent is the delivered agent with the lowest efficiency; it is `null` when there are no packages.

## Assumptions

The assignment leaves a few operational details open, so the simulator uses these
deterministic rules:

- Assignment uses each agent's starting position for every package. An agent's
  movement while delivering an earlier package does not change later assignments.
- Packages assigned to one agent are delivered in the same order as they appear
  in the input JSON. This is a simple, reproducible daily route.
- An agent travels from its current position to each package's warehouse, then
  directly to that package's destination. The agent remains at the destination
  until the next package; it does not return to a warehouse or depot.
- Distances use straight-line Euclidean geometry and are rounded to two decimal
  places in the report. The best agent is selected using the unrounded totals,
  with agent ID as the deterministic tie-breaker.
- Delivery delays, traffic, and mid-day agent changes are not part of the core
  input contract, so they are not invented for the required report.

## Test

Run all supplied fixtures and validation tests with:

```powershell
pytest -q
```
