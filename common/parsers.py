from datetime import datetime
from pygrok import Grok

from common.models import ChatEvent, KillfeedEvent, LoginEvent

# you don't really "need" grok, but YOU SHOULD use it
# unless you want to rawdog regex like a madman;
# feel free to look it up but beware that GROK patterns
# are usually used for logs parsing in tools like Datadog
# here's a playground https://grokdebugger.com/
# NOTE: these are based on MORDHAU
GROK_KILLFEED_EVENT = r"%{WORD:event_type}: %{NOTSPACE:date}: (?:%{NOTSPACE:killer_id})? \(%{GREEDYDATA:user_name}\) killed (?:%{NOTSPACE:killed_id})? \(%{GREEDYDATA:killed_user_name}\)"
GROK_LOGIN_EVENT = r"%{WORD:event_type}: %{NOTSPACE:date}: %{GREEDYDATA:user_name} \(%{WORD:player_id}\) logged %{WORD:instance}"
DATE_FORMAT = r"%Y.%m.%d-%H.%M.%S"
GROK_CHAT_EVENT = r"%{WORD:event_type}: %{NOTSPACE:player_id}, %{GREEDYDATA:user_name}, \(%{WORD:channel}\) %{GREEDYDATA:message}"


def parse_event(event: str, grok_pattern: str) -> tuple[bool, dict[str, str]]:
    pattern = Grok(grok_pattern)
    match = pattern.match(event)
    if not match:
        return (False, match)
    else:
        return (True, match)


def parse_killfeed_event(event: str) -> KillfeedEvent | None:
    (success, parsed) = parse_event(event, GROK_KILLFEED_EVENT)
    if not success:
        return None
    return KillfeedEvent(**parsed)


def parse_login_event(event: str) -> LoginEvent | None:
    (success, parsed) = parse_event(event, GROK_LOGIN_EVENT)
    if not success:
        return None
    return LoginEvent(**parsed)


def parse_chat_event(event: str) -> ChatEvent | None:
    (success, parsed) = parse_event(event, GROK_CHAT_EVENT)
    if not success:
        return None
    return ChatEvent(**parsed)


def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, DATE_FORMAT)
