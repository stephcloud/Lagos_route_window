import json
from pathlib import Path
from typing import TypedDict

class RouteRecord(TypedDict):
    route_number: int
    name: str
    start: str
    end: str
    fare_naira: int
    stops: list[str]


class BusRecord(TypedDict):
    plate: str
    bus_type: str
    route_number: int
    driver: str
    seats: int

class UnionData(TypedDict):
    routes: list[RouteRecord]
    buses: list[BusRecord]


DATA_FILE: Path = Path(__file__).parent / "lagos_routes.json"

def load_data(path: Path = DATA_FILE) -> UnionData:
    with open(path, "r", encoding="utf-8") as handle:
        raw: UnionData = json.load(handle)
    return raw