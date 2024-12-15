import asyncio
import struct
from contextlib import AbstractAsyncContextManager
from common import logger
from config_client.data import bot_config

# Packet types
SERVERDATA_AUTH = 3
SERVERDATA_EXECCOMMAND = 2
DEFAULT_RCON_CONNECT_TIMEOUT = 5


# src: https://github.com/pmrowla/pysrcds/blob/master/srcds/rcon.py
class RconPacket:
    """RCON packet"""

    def __init__(self, pkt_id=0, pkt_type=-1, body=""):
        self.pkt_id = pkt_id
        self.pkt_type = pkt_type
        self.body = body

    def __str__(self):
        """Return the body string."""
        return self.body

    def size(self):
        """Return the pkt_size field for this packet."""
        return len(self.body) + 10

    def pack(self):
        """Return the packed version of the packet."""
        return struct.pack(
            "<3i{0}s".format(len(self.body) + 2),
            self.size(),
            self.pkt_id,
            self.pkt_type,
            bytearray(self.body, "utf-8"),
        )


# src: https://github.com/pmrowla/pysrcds/blob/master/srcds/rcon.py
def get_login_packet(pwd: str):
    serverdata_auth = 3
    b = bytes(1)
    b += bytes(serverdata_auth)
    b += pwd.encode()
    return b


class RconClient:
    _port: int
    _password: str
    _address: str
    _reader: asyncio.StreamReader
    _writer: asyncio.StreamWriter
    _counter: int
    _connect_timeout: int

    def __init__(self) -> None:
        self._port = bot_config.rcon_port
        self._connect_timeout = bot_config.rcon_connect_timeout
        self._password = bot_config.rcon_password
        self._address = bot_config.rcon_address
        self._counter = 0

    async def recv_pkt(self) -> RconPacket:
        """Read one RCON packet"""
        while True:
            header = await self._reader.read(struct.calcsize("<3i"))
            header_length = len(header)
            if header_length != 0:
                break
            else:
                await asyncio.sleep(1)

        (pkt_size, pkt_id, pkt_type) = struct.unpack("<3i", header)
        body_bytes = await self._reader.read(pkt_size - 8)
        body = body_bytes.decode()
        return RconPacket(pkt_id, pkt_type, body)

    def build_packet_id(self):
        self._counter += 1
        return self._counter

    async def rewarm(self):
        self._writer.write(
            RconPacket(self.build_packet_id(), SERVERDATA_EXECCOMMAND, "alive").pack()
        )
        await self._writer.drain()

    async def get_connection(self):
        conn: tuple[asyncio.StreamReader, asyncio.StreamWriter]
        async with asyncio.timeout(self._connect_timeout):
            conn = await asyncio.open_connection(self._address, self._port)
        return conn

    async def authenticate(self):
        connection = await self.get_connection()
        reader, writer = connection
        self._reader = reader
        self._writer = writer
        pkt_id = self.build_packet_id()
        writer.write(RconPacket(pkt_id, SERVERDATA_AUTH, self._password).pack())
        await writer.drain()
        auth_response = await self.recv_pkt()
        if auth_response.pkt_id != pkt_id:
            raise ValueError(
                f"AUTHENTICATION FAILURE, MISMATCHING PKT ID INPUT={pkt_id}; OUTPUT={auth_response.pkt_id}"
            )

    async def execute(self, command: str, msg_type: int = SERVERDATA_EXECCOMMAND):
        pckt_id = self.build_packet_id()
        self._writer.write(RconPacket(pckt_id, msg_type, command).pack())
        await self._writer.drain()
        response = await self.recv_pkt()
        if response.pkt_id != pckt_id:
            raise ValueError(
                f"PACKET ID MISMATCH INPUT={pckt_id}; OUTPUT={response.pkt_id}"
            )
        return response.body


class RconContext(RconClient, AbstractAsyncContextManager):
    def __init__(self) -> None:
        RconClient.__init__(self)

    async def __aenter__(self) -> RconClient:
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._writer.close()
        async with asyncio.timeout(10):
            await self._writer.wait_closed()


async def main():
    async with RconContext() as client:
        r = await client.execute("info")
        logger.info(f"\n{r}")


if __name__ == "__main__":
    asyncio.run(main())
