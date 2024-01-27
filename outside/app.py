import asyncio

from rich.console import Console

from .airfr.client import FlightRadarClient
from .train.client import TrainClient


class OutsideApp:
    def __init__(self):
        self.msg_q = asyncio.Queue()
        self.console = Console()
        # clients
        self.air = FlightRadarClient(self.msg_q)
        self.train = TrainClient(self.msg_q)

    async def load(self):
        self.console.clear()
        await asyncio.gather(self.air.load())

    async def main(self):
        await self.load()
        await asyncio.sleep(0.5)
        self.console.clear()
        # run forever
        while True:
            msg = await self.msg_q.get()
            self.console.print(msg)
