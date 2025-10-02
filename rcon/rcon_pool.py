import asyncio
from common import logger
from rcon.rcon import RconClient


class RconConnectionPool:
    _pool: asyncio.Queue[RconClient]
    _in_use: set[RconClient]

    def __init__(self, max_size: int = 10) -> None:
        self._max_size = max_size
        self._pool: asyncio.Queue[RconClient] = asyncio.Queue(maxsize=max_size)
        self._lock = asyncio.Lock()
        self._in_use: set[RconClient] = set()

    async def generate_client(self):
        client = RconClient()
        await client.authenticate()

    async def get_client(self) -> RconClient:
        if self._pool.empty():
            async with self._lock:
                total_clients = len(self._in_use) + self._pool.qsize()
                logger.debug(f"Total clients: {total_clients}")
                if total_clients < self._max_size:
                    client = RconClient()
                    logger.debug(f"Created client {client.id}, authenticating...")
                    await client.authenticate()
                    self._in_use.add(client)
                    return client
        # if we're here it means we couldnt create new client
        if self._pool.empty():
            logger.debug("All clients busy, waiting...")
        client = await self._pool.get()
        logger.debug(f"Polled client {client.id} from pool")
        while client is not None and client.age_since_used > 60:
            logger.debug(f"Client {client.id} stale, dropping...")
            await client.close()
            client = None
            if not self._pool.empty():
                client = await self._pool.get()
                logger.debug(f"Polled freshier client {client.id} from pool")
        if client is None:
            logger.debug("No fresh clients available, recursing...")
            return await self.get_client()
        async with self._lock:
            self._in_use.add(client)
        return client

    async def release_client(self, client: RconClient) -> None:
        async with self._lock:
            total_clients = len(self._in_use) + self._pool.qsize()
            logger.debug(
                f"releasing client {client.id}, total clients: {total_clients}"
            )
            if client in self._in_use:
                self._in_use.remove(client)
                logger.debug("Releasing RCON client")
                await self._pool.put(client)
            else:
                logger.error(
                    f"Attempted to release a client ({client.id}) not part of the pool"
                )

    async def discard_client(self, client: RconClient):
        async with self._lock:
            try:
                if client in self._in_use:
                    self._in_use.remove(client)
                await client.close()
            except Exception as e:
                logger.error(
                    f"Attempted to close client {client.id}, failed with error {e}"
                )

    async def close_all(self) -> None:
        async with self._lock:
            while not self._pool.empty():
                client = await self._pool.get()
                await client.close()
            for client in self._in_use:
                await client.close()
            self._in_use.clear()
            self._pool = asyncio.Queue(maxsize=self._max_size)
