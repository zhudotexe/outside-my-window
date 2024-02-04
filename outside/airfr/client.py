import asyncio
import datetime
import json
from pathlib import Path

from fr24.livefeed import livefeed_message_create, livefeed_post, livefeed_request_create, livefeed_response_parse

from outside.bases import BaseClient
from outside.constants import E_BOUND, HOME_AIRPORT, N_BOUND, S_BOUND, W_BOUND
from outside.utils import a_or_an

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
        try:
            data = await asyncio.wait_for(livefeed_post(self.http, request), timeout=30)
        except asyncio.TimeoutError:
            return
        data = livefeed_response_parse(data)

        for flight in data.flights_list:
            if flight.flightid in self.finished_flights:
                continue
            self.finished_flights.add(flight.flightid)

            now = datetime.datetime.now().strftime("%H:%M")
            aircraft_type = self.aircraft_types.get(flight.extra_info.type, flight.extra_info.type)
            origin_airport = self.airport_names.get(flight.extra_info.route.from_, flight.extra_info.route.from_)
            destination_airport = self.airport_names.get(flight.extra_info.route.to, flight.extra_info.route.to)

            if flight.extra_info.route.from_ == HOME_AIRPORT:
                from_or_to_airport = f"to [b]{destination_airport}[/b]"
            else:
                from_or_to_airport = f"from [b]{origin_airport}[/b]"

            await self.q.put(
                f"[{now}][[bright_cyan]AIR[/bright_cyan]] That's flight [b]{flight.callsign}[/b]"
                f" {from_or_to_airport} - {a_or_an(aircraft_type, style='b')}."
            )
