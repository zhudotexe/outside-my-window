import datetime
from dataclasses import dataclass


@dataclass
class Station:
    name: str
    code: str
    tz: str
    bus: bool
    sch_arr: datetime.datetime
    sch_dep: datetime.datetime
    arr: datetime.datetime
    dep: datetime.datetime
    arr_comment: str
    dep_comment: str
    status: str


@dataclass
class Train:
    route_name: str
    train_num: int
    train_id: str
    lat: float
    long: float
    timely: str
    stations: list[Station]
    heading: str
    event_code: str
    event_tz: str
    event_name: str
    orig_code: str
    orig_tz: str
    orig_name: str
    dest_code: str
    dest_tz: str
    dest_name: str
    train_state: str
    velocity: float
    status_msg: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    last_val_ts: datetime.datetime
    object_id: int
