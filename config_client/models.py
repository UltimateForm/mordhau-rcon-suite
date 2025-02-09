from dataclasses import dataclass, field, fields
import json
import os
import aiofiles
from aiofiles import os as aos
from dacite import from_dict
from typing import Optional
from datetime import date


@dataclass
class IOBoundDataclass:
    @classmethod
    def delete(cls):
        os.remove(cls.get_path())

    @classmethod
    async def adelete(cls):
        await aos.remove(cls.get_path())

    @classmethod
    def exists(cls):
        return os.path.exists(cls.get_path())

    @classmethod
    async def aexists(cls):
        exists = await aos.path.exists(cls.get_path())
        return exists

    def as_dict(self):
        return self.__dict__

    def save(self):
        with open(self.get_path(), "w", encoding="utf8") as config_file:
            json.dump(self.as_dict(), config_file, indent=2)

    async def asave(self):
        async with aiofiles.open(self.get_path(), "w", encoding="utf8") as config_file:
            await config_file.write(json.dumps(self.as_dict(), indent=2))

    @classmethod
    def _load(cls):
        if not cls.exists():
            return cls()
        json_data: dict = None
        path = cls.get_path()
        with open(path, "r", encoding="utf8") as config_file:
            json_data = json.loads(config_file.read())
        config_data = from_dict(data_class=cls, data=json_data)
        return config_data

    @classmethod
    async def _aload(cls):
        exists = await cls.aexists()
        if not exists:
            return cls()
        path = cls.get_path()
        json_data: dict = None
        async with aiofiles.open(path, "r", encoding="utf8") as config_file:
            content = await config_file.read()
            json_data = json.loads(content)
        config_data = from_dict(data_class=cls, data=json_data)
        return config_data

    @classmethod
    def load(cls):
        return cls._load()

    @classmethod
    def aload(cls):
        return cls._aload()

    @classmethod
    def get_path(cls) -> str:
        pass


@dataclass
class BotConfig(IOBoundDataclass):
    info_channel: Optional[int] = None
    embed_footer_txt: Optional[str] = None
    embed_footer_icon: Optional[str] = None
    kills_channel: Optional[int] = None
    playtime_channel: Optional[int] = None
    season_channel: Optional[int] = None
    playtime_refresh_time: Optional[int] = None
    kills_refresh_time: Optional[int] = None
    info_refresh_time: Optional[int] = None
    season_refresh_time: Optional[int] = None
    ks_enabled: Optional[bool] = False
    chat_logs_channel: Optional[int] = None
    boards_min_to_format: Optional[int] = 100000
    config_bot_channel: int = 0
    rcon_password: str = ""
    rcon_address: str = "0.0.0.0"
    rcon_port: int = 7779
    rcon_connect_timeout: int = 30
    d_token: str = ""
    title: str = "KING"
    db_connection_string: str = "mongodb+srv://user:password@0.0.0.0"
    db_name: str = "db"
    experimental_bulk_listener: bool = False

    def info_board_enabled(self):
        return bool(self.info_channel)

    def playtime_board_enabled(self):
        return bool(self.playtime_channel)

    def kills_board_enabled(self):
        return bool(self.kills_channel)

    @classmethod
    def _load_from_env(cls):
        field_map: dict[str, str | int] = {}
        for field_item in fields(BotConfig):
            env_key = field_item.name.upper()
            field_type = field_item.type
            value = os.environ.get(env_key)
            if value is None:
                if field_type.__name__ != "Optional":
                    raise ValueError(
                        f"{env_key} is a required environment variable of type {field_type.__name__}"
                    )
                continue
            if (
                field_type is int
                or field_type is Optional[int]
                or field_type is bool
                or field_type is Optional[bool]
            ):
                value = int(value) if value.isnumeric() else 0
            if field_type is bool or field_type is Optional[bool]:
                value = bool(value)
            field_map[field_item.name] = value
        if len(field_map) == 0:
            return None
        else:
            return BotConfig(**field_map)

    @classmethod
    def load(cls):
        path = cls.get_path()
        if not os.path.exists(path):
            env_loaded = cls._load_from_env()
            if env_loaded:
                return env_loaded
        return cls._load()

    @classmethod
    def get_path(cls):
        return "./persist/bot.config.json"


@dataclass
class PtConfig(IOBoundDataclass):
    tags: dict[str, str]
    salutes: dict[str, str]
    playtime_tags: dict[str, str] = field(default_factory=dict)
    rename: dict[str, str] | None = field(default_factory=dict)
    tag_format: str = "[{0}]"
    salute_timer: int = 2

    @classmethod
    def get_path(cls):
        return "./persist/config.json"


@dataclass
class KsConfig(IOBoundDataclass):
    streak: dict[str, str | list[str]] = field(default_factory=dict)
    end: dict[str, str | list[str]] = field(default_factory=dict)
    firstblood: str = "{0} has claimed first blood"

    @classmethod
    def get_path(cls):
        return "./persist/ks.config.json"


@dataclass
class EmbedConfig:
    title: str = ""
    description: str = ""
    image_url: str = ""
    footer_txt: str = ""


@dataclass
class SeasonConfig(IOBoundDataclass):
    start_date: Optional[str] = field(init=False, default=None)
    end_date: Optional[str] = field(init=False, default=None)
    channel: Optional[int] = field(init=False, default=0)
    embed_config: EmbedConfig = field(init=False, default_factory=EmbedConfig)
    name: str = "Season Name"
    exclude: list[str] = field(default_factory=list)
    type: str = "kdr"
    created_date: str = field(init=False)

    @property
    def is_active(self):
        return bool(self.start_date and not self.end_date)

    def __post_init__(self):
        self.created_date = date.today().strftime("%d/%m/%Y")

    @classmethod
    def get_path(cls):
        return "./persist/season.config.json"

    def as_dict(self):
        self_dict = self.__dict__.copy()
        self_dict["embed_config"] = self.embed_config.__dict__
        return self_dict


if __name__ == "__main__":
    season_config = SeasonConfig()
    print(season_config)
