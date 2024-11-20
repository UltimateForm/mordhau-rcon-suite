import asyncio
import os
import config_client.main as config_client
from dotenv import load_dotenv
from boards.info import InfoBoard
from boards.kills import KillsScoreboard
from common import logger, parsers
from common.models import LoginEvent, PlayerStore
from common.discord import common_intents
from database.main import load_db
from persistent_titles.main import PersistentTitles
from migrant_titles.main import MigrantTitles, MigrantComputeEvent
from rcon.rcon_listener import RconListener
from db_kills.main import DbKills
from boards.playtime import PlayTimeScoreboard

load_dotenv()


async def main():
    db = load_db()
    config_client.DATABASE = db
    player_store = PlayerStore()
    login_listener = RconListener(event="login", listening=False)
    killfeed_listener = RconListener(event="killfeed", listening=False)
    migrant_titles = MigrantTitles(killfeed_listener, player_store)
    peristent_titles = PersistentTitles(login_listener)
    db_kills = DbKills(db["kills"], killfeed_listener, player_store)
    playtime_channel = int(os.environ.get("PLAYTIME_CHANNEL", 0))
    kills_channel = int(os.environ.get("KILLS_CHANNEL", 0))
    playtime_scoreboard = PlayTimeScoreboard(
        playtime_channel, db["playtime"], common_intents
    )
    kills_scoreboard = KillsScoreboard(kills_channel, db["kills"], common_intents)
    d_token = os.environ.get("D_TOKEN")

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

    login_listener.subscribe(populate_player_store)

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
        peristent_titles.start(db),
        playtime_scoreboard.start(token=d_token),
        kills_scoreboard.start(token=d_token),
        db_kills.start(),
    ]
    info_channel = int(os.environ.get("INFO_CHANNEL", 0))
    if info_channel:
        info_board = InfoBoard(info_channel, common_intents)
        tasks.append(info_board.start(token=os.environ.get("D_TOKEN")))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logger.use_date_time_logger()
    logger.info("INIT")
    asyncio.run(main())
    logger.info("END")
