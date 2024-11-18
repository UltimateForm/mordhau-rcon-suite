from dataclasses import dataclass


@dataclass
class SessionEvent:
    user_name: str
    playfab_id: str
    minutes: int
