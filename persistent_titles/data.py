from dataclasses import dataclass


@dataclass
class SessionEvent:
    playfab_id: str
    minutes: int
