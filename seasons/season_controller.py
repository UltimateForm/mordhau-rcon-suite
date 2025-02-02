import reactivex
from enum import Enum


class SeasonEvent(Enum):
    START = 1
    END = 2
    UPDATE = 3
    CREATE = 4
    DESTROY = 5


SEASON_TOPIC: reactivex.Subject[SeasonEvent] = reactivex.Subject()
