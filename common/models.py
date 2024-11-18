from dataclasses import dataclass


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
