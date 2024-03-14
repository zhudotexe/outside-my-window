from outside.bases import BaseClient


"""
belief: {trainid, lastupdated, pos, vel, windowstart, windowend}
"""

class TrainClient(BaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def get_trains(self):
        resp = await self.http.get("https://api-v3.amtraker.com/v3/trains")
        resp.raise_for_status()

    async def update_belief(self):
        """
        Get the trains, then for each train in the relevant area, update the belief of where the train currently is and
        when it will be visible outside my window
        """
