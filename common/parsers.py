from datetime import datetime
from pygrok import Grok
import re
from common.models import (
    ChatEvent,
    KillRecord,
    KillfeedEvent,
    LoginEvent,
    Player,
    ServerInfo,
)
from config_client.models import SeasonConfig

GROK_KILLFEED_EVENT = r"%{WORD:event_type}: %{NOTSPACE:date}: (?:%{NOTSPACE:killer_id})? \(%{GREEDYDATA:user_name}\) killed (?:%{NOTSPACE:killed_id})? \(%{GREEDYDATA:killed_user_name}\)"
GROK_LOGIN_EVENT = r"%{WORD:event_type}: %{NOTSPACE:date}: %{GREEDYDATA:user_name} \(%{WORD:player_id}\) logged %{WORD:instance}"
DATE_FORMAT = r"%Y.%m.%d-%H.%M.%S"
GROK_CHAT_EVENT = r"%{WORD:event_type}: %{NOTSPACE:player_id}, %{GREEDYDATA:user_name}, \(%{WORD:channel}\) %{GREEDYDATA:message}"
GROK_SERVER_INFO = r"HostName: %{GREEDYDATA:host}\nServerName: %{GREEDYDATA:server_name}\nVersion: %{GREEDYDATA:version}\nGameMode: %{GREEDYDATA:game_mode}\nMap: %{GREEDYDATA:map}"
GROK_PLAYERLIST_ROW = (
    r"%{NOTSPACE:player_id}, %{GREEDYDATA:user_name}, %{GREEDYDATA}, %{GREEDYDATA}"
)
GROK_MATCHSTATE = r"MatchState: %{GREEDYDATA:state}"


def parse_event(event: str, grok_pattern: str) -> tuple[bool, dict[str, str] | None]:
    pattern = Grok(grok_pattern)
    match = pattern.match(event)
    if not match:
        return (False, match)
    else:
        return (True, match)


def parse_killfeed_event(event: str) -> KillfeedEvent | None:
    (success, parsed) = parse_event(event, GROK_KILLFEED_EVENT)
    if not success or not parsed:
        return None
    return KillfeedEvent(**parsed)


def parse_login_event(event: str) -> LoginEvent | None:
    (success, parsed) = parse_event(event, GROK_LOGIN_EVENT)
    if not success or not parsed:
        return None
    return LoginEvent(**parsed)


def parse_chat_event(event: str) -> ChatEvent | None:
    without_new_lines = r" \ ".join(event.splitlines())
    (success, parsed) = parse_event(without_new_lines, GROK_CHAT_EVENT)
    if not success or not parsed:
        return None
    return ChatEvent(**parsed)


def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, DATE_FORMAT)


def parse_server_info(raw: str) -> ServerInfo | None:
    (success, parsed) = parse_event(raw, GROK_SERVER_INFO)
    if not success or not parsed:
        return None
    return ServerInfo(**parsed)


def parse_playerlist_row(raw: str) -> Player | None:
    (success, parsed) = parse_event(raw, GROK_PLAYERLIST_ROW)
    if not success or not parsed:
        return None
    return Player(**parsed)


def parse_playerlist(raw: str) -> list[Player]:
    rows = raw.splitlines()
    rows_parsed = [parse_playerlist_row(row) for row in rows]
    return [row for row in rows_parsed if row]


def parse_matchstate(raw: str) -> str | None:
    (success, parsed) = parse_event(raw, GROK_MATCHSTATE)
    if not success or not parsed:
        return None
    return parsed.get("state", None)


def transform_kill_record_to_db(
    record: KillRecord, season: SeasonConfig | None = None
) -> tuple[list[dict], dict]:
    update = {
        "$set": {"playfab_id": record.player_id, "user_name": record.user_name},
        "$inc": {},
    }

    death_updates = []

    total = 0
    for id, count in record.kills.items():
        update["$inc"][f"kills.{id}"] = count
        death_update = {"$set": {"playfab_id": id}, "$inc": {"death_count": count}}
        death_updates.append(death_update)
        if season and season.is_active:
            death_update["$inc"][f"season.{season.name}.death_count"] = count
        total += count
    update["$inc"]["kill_count"] = total
    if season and season.is_active:
        update["$inc"][f"season.{season.name}.kill_count"] = total
    return (death_updates, update)


def is_playfab_id_format(arg: str):
    return re.search(r"^([\S]{14,16})+$", arg) is not None
