import asyncio
from reactivex import Observable
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)
from pymongo import UpdateOne
from common.models import KillRecord, PlayerStore, KillfeedEvent
from common import logger, parsers
from seasons.season_controller import SEASON_TOPIC, SeasonEvent
from config_client.models import SeasonConfig


class DbKills:
    _collection: AsyncIOMotorCollection | None = None
    _pending_records: list[KillRecord] | None = None
    _bot_index = 0
    _player_store: PlayerStore | None = None
    _season: SeasonConfig | None = None

    def __init__(
        self,
        db_collection: AsyncIOMotorCollection,
        killfeed_observable: Observable[KillfeedEvent],
        player_store: PlayerStore,
        season: SeasonConfig | None,
    ):
        self._pending_records = []
        self._collection = db_collection
        self._player_store = player_store
        self._season = season
        SEASON_TOPIC.subscribe(lambda x: asyncio.create_task(self.load_season(x)))

        def _launch_kill_feed_task(event: KillfeedEvent):
            asyncio.create_task(self._process_killfeed(event))

        killfeed_observable.subscribe(_launch_kill_feed_task)

    async def load_season(self, event: SeasonEvent):
        if event is SeasonEvent.DESTROY:
            self._season = None
        else:
            self._season = await SeasonConfig.aload()

    async def _start_process(self):
        while True:
            await asyncio.sleep(60)
            records = [*self._pending_records]
            self._pending_records = []
            tasks = []
            for record in records:
                (death_updates, mutation) = parsers.transform_kill_record_to_db(
                    record, self._season
                )
                tasks.append(
                    UpdateOne({"playfab_id": record.player_id}, mutation, upsert=True)
                )
                for death_update in death_updates:
                    tasks.append(
                        UpdateOne(
                            {"playfab_id": death_update["$set"]["playfab_id"]},
                            death_update,
                        )
                    )
            if len(tasks) == 0:
                logger.debug("DbKills - No kill records to update")
                continue
            bulk_write = await self._collection.bulk_write(tasks)
            logger.debug(
                f"DbKills - Updated {len(tasks)} kill records: {bulk_write.bulk_api_result}"
            )

    async def _process_killfeed(self, kill_event: KillfeedEvent):
        try:
            if kill_event is None or kill_event.killed_id is None:
                return
            killed_id = kill_event.killed_id
            killer_id = kill_event.killer_id

            if kill_event is None or killed_id is None:
                return
            target: KillRecord = next(
                iter([el for el in self._pending_records if el.player_id == killer_id]),
                KillRecord(
                    killer_id,
                    self._player_store.players.get(killer_id, None)
                    or kill_event.user_name,
                    {},
                ),
            )
            if target.kills.get(killed_id, None):
                target.kills[killed_id] += 1
            else:
                target.kills[killed_id] = 1
            if target not in self._pending_records:
                self._pending_records.append(target)
        except Exception as e:
            logger.error(f"Something went wrong {e}")

    async def start(self):
        while True:
            try:
                await self._start_process()
            except Exception as e:
                logger.error(f"Error during kill record update routine: {e}")
