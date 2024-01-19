import asyncio
import datetime

import xmltodict

from outside.air.models import AIDXData, FlightData, FlightStatus
from outside.bases import BaseClient


class AirClient(BaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_update = datetime.datetime.fromtimestamp(0, datetime.UTC)
        self.finished_flights = set()
        self.flight_tasks: dict[str, asyncio.Task] = {}
        self.task = None

    async def load(self):
        await self.refresh()

        async def task():
            while True:
                await asyncio.sleep(300)
                await self.refresh()

        self.task = asyncio.create_task(task())
        await self.q.put("Air client loaded")

    async def refresh(self):
        # grab data from PHL IATA AIDX
        resp = await self.http.get("https://phl.org/drupalbin/flight-feed/airit.xml")
        resp.raise_for_status()
        data = xmltodict.parse(
            resp.content,
            process_namespaces=True,
            namespaces={
                "http://www.iata.org/IATA/2007/00": None,  # map IATA AIDX to root ns
                "http://www.airit.com/aidx": "ai",
            },
        )

        # parse them into the known flights, replacing the old known flights
        data = AIDXData.from_dict(data["IATA_AIDX_FlightLegRS"])
        self.last_update = data.timestamp

        # and schedule a task to emit when it actually happens, if when it happens is after now but before the next loop
        # or at least recheck it when the current est time happens
        for flight in data.flights:
            if flight.id in self.finished_flights:
                continue
            if (
                flight.relevant_time < self.last_update
                or not flight.is_inbound
                or flight.status == FlightStatus.CANCELLED
            ):
                self.finished_flights.add(flight.id)
                continue
            # if we are still waiting for this flight, cancel it and reissue the task with a more recent update
            if flight.id in self.flight_tasks:
                self.flight_tasks[flight.id].cancel()
            # issue a task to print when the flight is actually here
            self.flight_tasks[flight.id] = asyncio.create_task(self.future_flight_task(flight))

    async def future_flight_task(self, flight: FlightData):
        """When the flight is scheduled to land, add the message to the queue."""
        now = datetime.datetime.now(tz=datetime.UTC)
        secs_till_land = (flight.relevant_time - now).total_seconds()
        # print(
        #     f"Flight {flight.airline} {flight.flight_number} from {flight.departure_airport.name} lands in"
        #     f" {secs_till_land}"
        # )
        await asyncio.sleep(secs_till_land)
        await self.q.put(f"Landed: Flight {flight.airline} {flight.flight_number} from {flight.departure_airport.name}")
        # noinspection PyAsyncCall
        self.flight_tasks.pop(flight.id, None)
