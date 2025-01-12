import asyncio
from dc_player_commands.main import register_dc_player_commands
from config_client.data import pt_config, bot_config
from dotenv import load_dotenv
from boards.info import InfoBoard
from boards.kills import KillsScoreboard
from common import logger, parsers
from common.models import LoginEvent, PlayerStore
from common.discord import ObservableDiscordClient, common_intents
from database.main import load_db
from ingame_cmd.main import IngameCommands
from persistent_titles.main import PersistentTitles
from migrant_titles.main import MigrantTitles, MigrantComputeEvent
from rcon.rcon_listener import RconListener
from db_kills.main import DbKills
from boards.playtime import PlayTimeScoreboard
from killstreaks.main import KillStreaks
from discord.ext.commands import Bot
from reactivex import operators
from common.parsers import parse_chat_event, parse_login_event, parse_killfeed_event

load_dotenv()


async def main():
    db = load_db()
    dc_bot = Bot(command_prefix=".", intents=common_intents, help_command=None)
    d_token = bot_config.d_token
    dc_client = ObservableDiscordClient(intents=common_intents)
    register_dc_player_commands(dc_bot, db)
    player_store = PlayerStore()
    events_to_listen = ["login", "killfeed", "chat"]
    if bot_config.ks_enabled:
        events_to_listen.append("matchstate")
    bulk_listener = RconListener(event=events_to_listen)
    login_events = bulk_listener.pipe(
        operators.filter(lambda x: x.startswith("Login")),
        operators.map(parse_login_event),
    )
    killfeed_events = bulk_listener.pipe(
        operators.filter(lambda x: x.startswith("Killfeed")),
        operators.map(parse_killfeed_event),
    )
    chat_events = bulk_listener.pipe(
        operators.filter(lambda x: x.startswith("Chat")),
        operators.map(parse_chat_event),
    )
    migrant_titles = MigrantTitles(killfeed_events, player_store)
    peristent_titles = PersistentTitles(login_events, dc_bot)
    ingame_commands = IngameCommands(pt_config, db)
    db_kills = DbKills(db["kills"], killfeed_events, player_store)
    killstreaks = KillStreaks() if bot_config.ks_enabled else None
    playtime_channel = bot_config.playtime_channel
    kills_channel = bot_config.kills_channel
    playtime_scoreboard = PlayTimeScoreboard(
        db["playtime"], playtime_channel, bot_config.playtime_refresh_time
    )
    kills_scoreboard = KillsScoreboard(
        db["kills"], kills_channel, bot_config.kills_refresh_time
    )
    if bot_config.info_board_enabled():
        info_board = InfoBoard(bot_config.info_channel, bot_config.info_refresh_time)
        dc_client.subscribe(info_board)
    chat_events.subscribe(ingame_commands)
    dc_client.subscribe(playtime_scoreboard)
    dc_client.subscribe(kills_scoreboard)

    tasks = [
        bulk_listener.start(),
        peristent_titles.start(db),
        db_kills.start(),
        dc_bot.start(token=d_token),
        dc_client.start(token=d_token),
    ]

    if killstreaks:
        matchstate_listener = RconListener("matchstate")

        def matchstate_next(raw: str):
            state = parsers.parse_matchstate(raw)
            if not state:
                return
            stripped_state = state.strip("\x00")
            if stripped_state.lower() == "in progress":
                killstreaks.reset()

        matchstate_listener.subscribe(matchstate_next)
        killfeed_events.subscribe(killstreaks)

    def entrance_desk(player: LoginEvent):
        try:
            if player is None:
                return
            if player.instance == "out":
                if migrant_titles.rex_compute.current_rex == player.player_id:
                    migrant_titles.rex_compute.current_rex = ""
                player_store.players.pop(player.player_id, None)
                if killstreaks:
                    asyncio.create_task(
                        killstreaks.self_end_ks(player.user_name, player.player_id)
                    )
            else:
                player_store.players[player.player_id] = player.user_name
        except Exception as e:
            logger.error(
                f"Failed to populate player store with event '{player}'; Error: {e}"
            )

    login_events.subscribe(entrance_desk)

    def handle_tag_for_removed_rex(event: MigrantComputeEvent):
        logger.debug(f"handle_tag_for_removed_rex {event}")
        if event.event_type != "removed":
            return
        asyncio.create_task(
            peristent_titles.login_observer.handle_tag(
                LoginEvent("Login", "", event.user_name, event.playfab_id, "in")
            )
        )

    migrant_titles.rex_compute.subscribe(handle_tag_for_removed_rex)

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logger.use_date_time_logger()
    logger.info("INIT")
    asyncio.run(main())
    logger.info("END")
