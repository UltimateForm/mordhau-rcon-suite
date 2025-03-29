import logging


def use_date_time_logger():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("./persist/bot.log", mode="w"),
        ],
    )


def info(msg: str):
    logging.info(msg)


def warning(msg: str):
    logging.warning(msg)


def error(msg: str):
    logging.error(msg)


def debug(msg: str):
    logging.debug(msg)
