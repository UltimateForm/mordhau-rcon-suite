from dataclasses import dataclass, field

from common.compute import compute_time_txt


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
    rank: int | None
    kills: dict[str, int] = field(default_factory=dict)
    achievements: dict[str, int] = field(default_factory=dict)
    ratio: float | None = field(init=False)

    def __post_init__(self):
        self.ratio = (
            round(self.kill_count / self.death_count, 2)
            if self.death_count > 0
            else None
        )
        self.achievements = dict(
            [item for item in self.achievements.items() if item[1] is not None]
        )
