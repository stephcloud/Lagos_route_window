# The Lagos Route Window

A read-only FastAPI service over the union's routes and buses. GET only, no changes.

## Project layout

```
lagos-route-window/
  app/
    __init__.py
    data.py            # loads lagos_routes.json once, at startup
    main.py            # the window: endpoints and doorway rules
    lagos_routes.json  # the union's records (28 routes, 60 buses)
  requirements.txt
  .gitignore
  README.md
```

## Setup

Create a virtual environment and install dependencies. The venv itself is
listed in `.gitignore` and never gets committed, because a venv is tied to
one machine's Python install and OS. Anyone cloning this repo should build
their own from `requirements.txt` rather than inherit yours.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running it

```bash
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs` for the interactive testing page.

## Endpoints

- `GET /` — welcome message plus how many routes and buses the union runs today.
- `GET /routes/{route_number}` — full details of one route. `route_number` must be 1 to 200.
- `GET /routes/{route_number}/stops` — the stops of one route, paged with `?limit=` (1 to 10, default 5) and `?skip=` (0 or more).
- `GET /routes/{route_number}/buses` — every bus serving one route (bonus).
- `GET /buses/{plate}` — one bus by plate. Plates must match `AAA-999AA`.
- `GET /fleet/{bus_type}` — every bus of one kind. `bus_type` is one of `brt`, `danfo`, `keke`.
- `GET /search?destination=...&max_fare=...&sort=fare` — every route whose stops include `destination` (3 to 30 characters, required), optionally capped at `max_fare` (must be greater than 0), optionally sorted by fare (bonus).

## The doorway rule, and where it lives

Every constraint the chairman asked for is declared as type metadata on
the function signature, not as an `if` statement in the function body. One
example, from `app/main.py`:

```python
RouteNumberPath = Annotated[
    int,
    Path(title="Route number", description="Lagos route numbers run from 1 to 200.", ge=1, le=200),
]
```

This single alias is reused on `/routes/{route_number}`,
`/routes/{route_number}/stops`, and `/routes/{route_number}/buses`, so the
1-to-200 rule is written once and enforced identically on all three routes.

On `/docs`, open any of those three endpoints and look at the `route_number`
parameter: it shows the description, and a request outside 1-200 fails
before your browser even finishes typing it into "Try it out" (FastAPI
renders the `ge`/`le` bounds right there in the parameter panel, and returns
a 422 with the reason if you submit an out-of-range value).

The same pattern applies everywhere else: `PlatePath` carries the regex for
the plate shape, `BusType` is an `Enum` so `/docs` renders `brt` / `danfo` /
`keke` as a dropdown instead of a text box, and the `/search` query
parameters carry `min_length`, `max_length`, and `gt=0` directly. None of
the endpoint functions contain a validation `if` — only 404 checks for
"does this exist," which is business logic, not doorway validation.
