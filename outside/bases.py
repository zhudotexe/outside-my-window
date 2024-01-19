import asyncio
import enum
from abc import ABC
from datetime import datetime

import httpx


class BaseClient(ABC):
    def __init__(self, q=None):
        """
        :param q: An asyncio queue to send messages to the application terminal.
        """
        if q is None:
            q = asyncio.Queue()

        self.http = httpx.AsyncClient()
        self.q = q

    async def load(self):
        """Load the initial list of arrivals/departures and dispatch tasks to emit when they are outside my window."""
        raise NotImplementedError

    async def close(self):
        await self.http.aclose()


# ==== transit entity ====
class TransitDirection(enum.Enum):
    INBOUND = 0
    OUTBOUND = 1


class TransitStatus(enum.Enum):
    ON_TIME = 0
    DELAYED = 1
    EARLY = 2
    CANCELLED = 3
    OTHER = -1


class Transit:
    def __init__(
        self,
        direction: TransitDirection,
        code: str,  # flight or train number
        time: datetime,  # time it departed or arrived
        destination: str,  # full city name of its destination (or source, if arriving)
        destination_code: str,  # airport/station code
        status: TransitStatus,
        delay_min: float,
    ):
        self.direction = direction
        self.code = code
        self.time = time
        self.destination = destination
        self.destination_code = destination_code
        self.status = status
        self.delay_min = delay_min

    def __eq__(self, other):
        return isinstance(other, Transit) and self.code == other.code
