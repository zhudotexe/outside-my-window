import asyncio
import json
from pathlib import Path

from fr24.livefeed import livefeed_message_create, livefeed_post, livefeed_request_create, livefeed_response_parse

from outside.bases import BaseClient
from outside.constants import E_BOUND, N_BOUND, S_BOUND, W_BOUND

REFRESH_TIME = 8  # fr24 site refreshes every 8 sec; we will too
DATA_PATH = Path(__file__).parent / "data"


class FlightRadarClient(BaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.finished_flights = set()
        self.task = None
        self.airport_names = {}
        self.aircraft_types = {}

    async def load(self):
        # load aircraft
        with open(DATA_PATH / "AircraftFamily.json") as f:
            aircraft = json.load(f)
            for family in aircraft:
                for model in family["models"]:
                    self.aircraft_types[model["id"]] = model["name"]

        # load airports
        with open(DATA_PATH / "Airports.json") as f:
            airports = json.load(f)
            for airport in airports:
                self.airport_names[airport["iata"]] = airport["label"]

        # spawn forever task
        self.task = asyncio.create_task(self.poll_live())

    async def poll_live(self):
        """Task to process all flights in the bounds forever."""
        while True:
            await self.process_flights()
            await asyncio.sleep(REFRESH_TIME)

    async def process_flights(self):
        # request fr24 live data
        message = livefeed_message_create(north=N_BOUND, west=W_BOUND, south=S_BOUND, east=E_BOUND)
        request = livefeed_request_create(message)
        data = await livefeed_post(self.http, request)
        data = livefeed_response_parse(data)

        for flight in data.flights_list:
            if flight.flightid in self.finished_flights:
                continue
            self.finished_flights.add(flight.flightid)

            aircraft_type = self.aircraft_types.get(flight.extra_info.type, flight.extra_info.type)
            origin_airport = self.airport_names.get(flight.extra_info.route.from_, flight.extra_info.route.from_)

            await self.q.put(f"Airplane: That's flight {flight.callsign} from {origin_airport} - a {aircraft_type}.")
