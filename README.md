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

## Delivery rules

- Both supplied input shapes are supported: ID-keyed dictionaries and lists of records.
- A package is assigned using Euclidean distance from each agent's initial location to the package warehouse.
- Ties are resolved by agent ID so results are repeatable.
- Each agent delivers assigned packages in their input order. For every package, the route is the agent's current position to the warehouse, then from the warehouse to the destination.
- `efficiency` is total distance divided by packages delivered. Agents with no packages have efficiency `0.0`.
- The best agent is the delivered agent with the lowest efficiency; it is `null` when there are no packages.

## Test

Run all supplied fixtures and validation tests with:

```powershell
pytest -q
```
