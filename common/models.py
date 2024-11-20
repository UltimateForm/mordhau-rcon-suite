from dataclasses import dataclass, field


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
class PlayerListRow:
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
