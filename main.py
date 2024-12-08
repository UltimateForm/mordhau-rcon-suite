import asyncio
import config_client.main as config_client
from config_client.data import pt_config, bot_config
from dotenv import load_dotenv
from boards.info import InfoBoard
from boards.kills import KillsScoreboard
from common import logger, parsers
from common.models import LoginEvent, PlayerStore
from common.discord import common_intents
from database.main import load_db
from ingame_cmd.main import IngameCommands
from persistent_titles.main import PersistentTitles
from migrant_titles.main import MigrantTitles, MigrantComputeEvent
from rcon.rcon_listener import RconListener
from db_kills.main import DbKills
from boards.playtime import PlayTimeScoreboard
from killstreaks.main import KillStreaks

load_dotenv()


async def main():
    db = load_db()
    config_client.DATABASE = db
    player_store = PlayerStore()
    login_listener = RconListener(event="login", listening=False)
    killfeed_listener = RconListener(event="killfeed", listening=False)
    chat_listener = RconListener("chat")
    migrant_titles = MigrantTitles(killfeed_listener, player_store)
    peristent_titles = PersistentTitles(login_listener)
    ingame_commands = IngameCommands(pt_config, db)
    db_kills = DbKills(db["kills"], killfeed_listener, player_store)
    playtime_channel = bot_config.playtime_channel
    kills_channel = bot_config.kills_channel
    playtime_scoreboard = PlayTimeScoreboard(
        playtime_channel, db["playtime"], common_intents
    )
    kills_scoreboard = KillsScoreboard(kills_channel, db["kills"], common_intents)
    d_token = bot_config.d_token

    def populate_player_store(raw: str):
        try:
            player = parsers.parse_login_event(raw)
            if player is None:
                return
            if player.instance == "out":
                player_store.players.pop(player.player_id, None)
            else:
                player_store.players[player.player_id] = player.user_name
        except Exception as e:
            logger.error(
                f"Failed to populate player store with event '{raw}'; Error: {e}"
            )

    chat_listener.subscribe()
    login_listener.subscribe(populate_player_store)
    chat_listener.subscribe(ingame_commands)

    if bot_config.ks_enabled:
        killstreaks = KillStreaks()
        killfeed_listener.subscribe(killstreaks)

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
    tasks = [
        login_listener.start(),
        killfeed_listener.start(),
        chat_listener.start(),
        peristent_titles.start(db),
        playtime_scoreboard.start(token=d_token),
        kills_scoreboard.start(token=d_token),
        db_kills.start(),
    ]
    if bot_config.info_board_enabled():
        info_channel = bot_config.info_channel
        info_board = InfoBoard(info_channel, common_intents)
        tasks.append(info_board.start(d_token))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logger.use_date_time_logger()
    logger.info("INIT")
    asyncio.run(main())
    logger.info("END")
