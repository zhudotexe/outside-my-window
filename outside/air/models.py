import datetime
import enum
from dataclasses import dataclass

from outside.constants import HOME_AIRPORT


class FlightStatus(enum.Enum):
    # PublicStatus
    DIVERTED = "DV"
    CANCELLED = "DX"  # also internal XLD
    # est > sch + 30
    DELAYED = "DELAYED"
    # ai:InternalStatus
    DEPARTED = "OFB"
    AIRBORNE = "OFF"
    LANDED = "TD"
    IN_RANGE = "TMO"
    EN_ROUTE = "UOT"
    ON_TIME = "SCH"


@dataclass
class AirportInfo:
    code: str
    name: str


@dataclass
class FlightData:
    id: str
    airline: str
    flight_number: str
    departure_airport: AirportInfo
    arrival_airport: AirportInfo
    origin_date: datetime.date
    status: FlightStatus
    scheduled_time: datetime.datetime  # TimeType == SCT
    estimated_time: datetime.datetime | None  # TimeType == EST
    actual_time: datetime.datetime | None  # OperationQualifier == TDN/TKO; TimeType == ACT
    tail_number: str | None

    @property
    def is_inbound(self):
        return self.arrival_airport.code == HOME_AIRPORT

    @property
    def relevant_time(self):
        return (
            self.actual_time
            if self.actual_time
            else self.estimated_time
            if self.estimated_time
            else self.scheduled_time
        )

    @classmethod
    def from_dict(cls, d: dict):
        li = d["LegIdentifier"]
        ld = d["LegData"]

        # airports
        departure_code = li["DepartureAirport"]
        arrival_code = li["ArrivalAirport"]
        departure_airport_data = next(a for a in ld["ai:AirportInfo"]["ai:Airport"] if a["@code"] == departure_code)
        arrival_airport_data = next(a for a in ld["ai:AirportInfo"]["ai:Airport"] if a["@code"] == arrival_code)
        departure_airport = AirportInfo(
            code=departure_airport_data["@code"],
            name=departure_airport_data.get("ai:AirportName", departure_airport_data["@code"]),
        )
        arrival_airport = AirportInfo(
            code=arrival_airport_data["@code"],
            name=arrival_airport_data.get("ai:AirportName", arrival_airport_data["@code"]),
        )

        # time
        is_delayed = False
        ot = ld["OperationTime"]
        if not isinstance(ot, list):
            ot = [ot]
        scheduled_time_data = next((t for t in ot if t["@TimeType"] == "SCT"), None)
        estimated_time_data = next((t for t in ot if t["@TimeType"] == "EST"), None)
        actual_time_data = next((t for t in ot if t["@TimeType"] in ("TDN", "TKO")), None)

        scheduled_time = datetime.datetime.fromisoformat(scheduled_time_data["#text"])
        if estimated_time_data:
            estimated_time = datetime.datetime.fromisoformat(estimated_time_data["#text"])
            is_delayed = estimated_time - scheduled_time >= datetime.timedelta(minutes=30)
        else:
            estimated_time = None
        if actual_time_data:
            actual_time = datetime.datetime.fromisoformat(actual_time_data["#text"])
            is_delayed = actual_time - scheduled_time >= datetime.timedelta(minutes=30)
        else:
            actual_time = None

        # status
        ps = ld["PublicStatus"]
        ins = ld["ai:InternalStatus"]
        if ps == "DV":
            status = FlightStatus.DIVERTED
        elif ps == "DX":
            status = FlightStatus.CANCELLED
        elif is_delayed:
            status = FlightStatus.DELAYED
        elif ins == "TD":
            status = FlightStatus.LANDED
        elif ins == "TMO":
            status = FlightStatus.IN_RANGE
        elif ins == "OFB":
            status = FlightStatus.DEPARTED
        elif ins == "OFF":
            status = FlightStatus.AIRBORNE
        elif ins == "UOT":
            status = FlightStatus.EN_ROUTE  # unknown when this shows up
        elif ins == "XLD":
            status = FlightStatus.CANCELLED
        else:  # SCH
            status = FlightStatus.ON_TIME

        aircraft_info = ld["AircraftInfo"]
        tail_number = None
        if aircraft_info:
            tail_number = aircraft_info.get("Registration")

        return cls(
            id=li["ai:InternalId"],
            airline=li["Airline"],
            flight_number=li["FlightNumber"],
            departure_airport=departure_airport,
            arrival_airport=arrival_airport,
            origin_date=datetime.date.fromisoformat(li["OriginDate"]),
            status=status,
            scheduled_time=scheduled_time,
            estimated_time=estimated_time,
            actual_time=actual_time,
            tail_number=tail_number,
        )


@dataclass
class AIDXData:
    timestamp: datetime.datetime
    id: str
    flights: list[FlightData]

    @classmethod
    def from_dict(cls, d: dict):
        flights = list(map(FlightData.from_dict, d["FlightLeg"]))
        return cls(
            timestamp=datetime.datetime.fromisoformat(d["@TimeStamp"]),
            id=d["@TransactionIdentifier"],
            flights=flights,
        )
