import asyncio
from reactivex import Subject, operators
from rcon.rcon import RconClient
from common import logger

RECONNECT_WAIT_TIME_SECS = 5


class RconListener(Subject[str], RconClient):
    _event: str
    _port: int
    _password: str
    _address: str

    _listening: bool

    def __init__(self, event: str = "chat", listening: bool = False) -> None:
        self._event = event
        self._listening = listening
        Subject.__init__(self)
        RconClient.__init__(self)

    async def warmer(self):
        while True:
            await asyncio.sleep(100)
            try:
                logger.debug(f"{self._event} listener: Rewarming...")
                async with asyncio.timeout(self._connect_timeout):
                    await self.rewarm()
                logger.debug(f"{self._event} listener: Rewarm complete")
            except Exception as e:
                logger.error(
                    f"{self._event} listener: FAILED TO REWARM! ERROR: {str(e)}"
                )

    async def _start(self, listening: bool = False):
        rewarm_task: asyncio.Task | None = None
        try:
            logger.info(f"{self._event} listener: authenticating...")
            await self.authenticate()
            logger.info(f"{self._event} listener: authentication complete")
            if not listening:
                r = await self.execute(f"listen {self._event}")
                logger.info(f"{self._event} listener: {r}")
            rewarm_task = asyncio.create_task(self.warmer())
            while True:
                pck = await self.recv_pkt()
                self.on_next(pck.body)
        except Exception:
            if rewarm_task:
                rewarm_task.cancel()
            raise

    async def start(self):
        while True:
            try:
                logger.info(f"{self._event} listener: Initiating...")
                await self._start(self._listening)
                return
            except Exception as e:
                logger.error(
                    f"{self._event} listener:  Connection error occured: {str(e) or type(e).__name__}. Attempting reconnection in {RECONNECT_WAIT_TIME_SECS} seconds..."
                )
                await asyncio.sleep(RECONNECT_WAIT_TIME_SECS)


if __name__ == "__main__":
    logger.use_date_time_logger()
    login_listener = RconListener(event="login", listening=False)
    login_listener.pipe(operators.filter(lambda x: x.startswith("Login:"))).subscribe(
        on_next=lambda x: logger.info(f"LOGIN: {x}")
    )

    chat_listener = RconListener(event="chat", listening=False)
    chat_listener.pipe(operators.filter(lambda x: x.startswith("Chat:"))).subscribe(
        on_next=lambda x: logger.info(f"CHAT: {x}")
    )

    async def main():
        await asyncio.gather(chat_listener.start(), login_listener.start())

    asyncio.run(main())
