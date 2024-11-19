import asyncio
import os
from dotenv import load_dotenv
from boards.info import InfoBoard
from common import logger
from common.models import LoginEvent
from common.discord import common_intents
from database.main import load_db
from persistent_titles.main import PersistentTitles
from migrant_titles.main import MigrantTitles, MigrantComputeEvent
from rcon.rcon_listener import RconListener

from boards.playtime import PlayTimeScoreboard

load_dotenv()


async def main():
    db_collections = load_db()
    login_listener = RconListener(event="login", listening=False)
    migrant_titles = MigrantTitles(login_listener)
    peristent_titles = PersistentTitles(login_listener)
    playtime_channel = int(os.environ.get("PLAYTIME_CHANNEL", 0))

    playtime_scoreboard = PlayTimeScoreboard(
        playtime_channel, db_collections[1], common_intents
    )

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
        migrant_titles.start(),
        peristent_titles.start(db_collections),
        playtime_scoreboard.start(token=os.environ.get("D_TOKEN")),
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
