import asyncio
from dotenv import load_dotenv
from common import logger
from persistent_titles.main import PersistentTitles
from migrant_titles.main import MigrantTitles, MigrantComputeEvent
from rcon.rcon_listener import RconListener

load_dotenv()


async def main():
    login_listener = RconListener(event="login", listening=False)
    migrant_titles = MigrantTitles(login_listener)
    peristent_titles = PersistentTitles(login_listener)

    def handle_tag_for_removed_rex(event: MigrantComputeEvent):
        logger.debug(f"handle_tag_for_removed_rex {event}")
        if event.event_type != "removed":
            return
        asyncio.create_task(
            peristent_titles.login_observer.handle_tag(
                {"playfabId": event.playfab_id, "userName": event.user_name}
            )
        )

    migrant_titles.rex_compute.subscribe(handle_tag_for_removed_rex)
    await asyncio.gather(
        login_listener.start(),
        migrant_titles.start(),
        peristent_titles.start(),
    )


if __name__ == "__main__":
    logger.use_date_time_logger()
    logger.info("INIT")
    asyncio.run(main())
    logger.info("END")
