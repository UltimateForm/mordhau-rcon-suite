from dataclasses import dataclass, field

from common.compute import compute_time_txt
from rcon.rcon_listener import RconListener


@dataclass
class KillfeedEvent:
    event_type: str
    date: str
    killer_id: str
    user_name: str
    killed_id: str
    killed_user_name: str


@dataclass
class LoginEvent:
    event_type: str
    date: str
    user_name: str
    player_id: str
    instance: str


@dataclass
class ChatEvent:
    event_type: str
    player_id: str
    user_name: str
    channel: str
    message: str


@dataclass
class ServerInfo:
    host: str
    server_name: str
    version: str
    game_mode: str
    map: str


@dataclass
class Player:
    player_id: str
    user_name: str


@dataclass
class KillRecord:
    player_id: str
    user_name: str
    kills: dict[str, int] = field(default_factory=dict)


@dataclass
class PlayerStore:
    players: dict[str, str] = field(default_factory=dict)


@dataclass
class PlaytimeScore(Player):
    minutes: int
    rank: int
    time_txt: str = field(init=False)

    def __post_init__(self):
        self.time_txt = compute_time_txt(self.minutes)


@dataclass
class KillScore(Player):
    kill_count: int
    death_count: int
    rank: int
    kills: dict[str, int] = field(default_factory=dict)
    achievements: dict[str, int] = field(default_factory=dict)
    ratio: int | None = field(init=False)

    def __post_init__(self):
        self.ratio = (
            round(self.kill_count / self.death_count, 2)
            if self.death_count > 0
            else None
        )


@dataclass
class RconListenerCollection:
    chat: RconListener
    killfeed: RconListener
    matchstate: RconListener
    login: RconListener
    bulk: RconListener
