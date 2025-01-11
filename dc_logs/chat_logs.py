import discord
from reactivex import Observer

from common.parsers import parse_chat_event


class ChatLogs(Observer[str]):
		_channel_id: int = 0

    def __init__(self, channel_id:int):
        self.
        super().__init__()

    def on_next(self, value):
        event_data = parse_chat_event(value)
        if not event_data:
            return

