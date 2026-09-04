from contextlib import asynccontextmanager
from enum import Enum
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel

from app.data import BusRecord, RouteRecord, UnionData, load_data


class Route(BaseModel):
    route_number: int
    name: str
    end: str
    fare_naira: int
    stops: list[str]


class Bus(BaseModel):
    plate: str
    bus_type: str
    route_number: int
    driver: str
    seats: int


class WelcomeResponse(BaseModel):
    message: str
    total_routes: int
    total_buses: int


class StopsResponses(BaseModel):
    route_number: int
    skip: int
    limit: int
    stops: list[str]


class BusType(str, Enum):
    brt = "brt"
    danfo = "danfo"
    keke = "keke"


class SortOption(str, Enum):
    fare = "fare"


RouteNumberPath = Annotated[
    int,
    Path(
        title="Route number",
        description="Lagos route numbers run from 1 to 200",
        ge=1,
        le=200,
    ),
]

PlatePath = Annotated[
    str,
    Path(
        title="Bus plate number",
        description=(
            "Lagos plates follow a strict shape: three capital letters,"
            "a dash, three digits, two capital letters -e.g. LSD-441KJ"
        ),
        pattern=r"^[A-Z]{3}-\d{3}[A-Z]{2}$",
    ),
]

_data: UnionData = {"routes": [], "buses": []}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _data
    _data = load_data()
    yield
    _data = {"routes": [], "buses": []}


app = FastAPI(
    title="The Lagos Route Window",
    description="All answers, no changes, a ready-only window onto the union's routes and buses.",
    lifespan=lifespan,
)


def _find_route(route_number: int) -> RouteRecord | None:
    for route in _data["routes"]:
        if route["route_number"] == route_number:
            return route
    return None


def _find_bus(plate: str) -> BusRecord | None:
    for bus in _data["buses"]:
        if bus["plate"] == plate:
            return bus
    return None


@app.get(
    "/", response_model=WelcomeResponse, summary="A welcome, and the day's numbers"
)
async def welcome() -> WelcomeResponse:
    return WelcomeResponse(
        message="Welcome to the Lagos Route Window.",
        total_routes=len(_data["routes"]),
        total_buses=len(_data["buses"]),
    )


@app.get(
    "/routes/{route_number}",
    response_model=Route,
    summary="Full details of one route",
)
async def read_route(route_number: RouteNumberPath) -> Route:
    route = _find_route(route_number)
    if route is None:
        raise HTTPException(
            status_code=404, detail=f"Route {route_number} was not found."
        )
    return Route(**route)


@app.get(
    "/routes/{route_number}/stops",
    response_model=StopsResponses,
    summary="The stops of one route, paged for a small phone screen",
)
async def read_route_stops(
    route_number: RouteNumberPath,
    limit: Annotated[
        int,
        Query(ge=1, le=10, description="How many stops to show at once."),
    ] = 5,
    skip: Annotated[
        int,
        Query(ge=0, description="How many stops to skip before showing results."),
    ] = 0,
) -> StopsResponses:
    route = _find_route(route_number)
    if route is None:
        raise HTTPException(
            status_code=404, detail=f"Route {route_number} was not found."
        )
    page = route["stops"][skip : skip + limit]
    return StopsResponses(route_number=route_number, skip=skip, limit=limit, stops=page)


@app.get(
    "/routes/{route_number}/buses",
    response_model=list[Bus],
    summary="Every bus serving one route (bonus)",
)
async def read_route_buses(route_number: RouteNumberPath) -> list[Bus]:
    route = _find_route(route_number)
    if route is None:
        raise HTTPException(
            status_code=404, detail=f"Route {route_number} was not found."
        )
    buses = [
        Bus(**bus) for bus in _data["buses"] if bus["route_number"] == route_number
    ]
    return buses


@app.get(
    "/buses/{plate}",
    response_model=Bus,
    summary="Details of one bus by its plate",
)
async def read_bus(plate: PlatePath) -> Bus:
    bus = _find_bus(plate)
    if bus is None:
        raise HTTPException(
            status_code=404, detail=f"No bus with plate {plate} was found."
        )
    return Bus(**bus)


@app.get(
    "/fleet/{bus_type}",
    response_model=list[Bus],
    summary="All buses of one kind",
)
async def read_fleet(
    bus_type: Annotated[
        BusType,
        Path(title="Kind of bus", description="The union runs exactly three kinds."),
    ],
) -> list[Bus]:
    return [Bus(**bus) for bus in _data["buses"] if bus["bus_type"] == bus_type.value]


@app.get(
    "/search",
    response_model=list[Route],
    summary="Every route whose stops include a destination",
)
async def search_routes(
    destination: Annotated[
        str,
        Query(
            min_length=3,
            max_length=30,
            description="A stop name to search for, 3 to 30 characters.",
        ),
    ],
    max_fare: Annotated[
        int | None,
        Query(gt=0, description="Keep only routes at or under this fare, in naira."),
    ] = None,
    sort: Annotated[
        SortOption | None,
        Query(description="Optionally sort the results by fare, ascending."),
    ] = None,
) -> list[Route]:
    target = destination.strip().lower()
    matches = [
        route
        for route in _data["routes"]
        if target in (stop.lower() for stop in route["stops"])
    ]

    if max_fare is not None:
        matches = [route for route in matches if route["fare_naira"] <= max_fare]

    if sort is SortOption.fare:
        matches = sorted(matches, key=lambda route: route["fare_naira"])

    return [Route(**route) for route in matches]
