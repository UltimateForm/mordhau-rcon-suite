import asyncio
from typing import Coroutine

from common import logger

TASKS: set[asyncio.Task] = set()


def backtask(coro: Coroutine):
    func_name = getattr(coro, "__name__", None)
    try:
        if func_name is None and hasattr(coro, "cr_code"):
            func_name = coro.cr_code.co_name  # type: ignore
        elif func_name is None:
            func_name = coro.__class__.__name__
    except Exception as e:
        logger.debug(f"Error getting function name: {e}")
        func_name = func_name or "unknown"

    task = asyncio.create_task(coro)
    TASKS.add(task)

    def cleanup(t: asyncio.Task):
        TASKS.discard(t)
        remaining_tasks = len(TASKS)
        task_name = t.get_name()
        logger.debug(
            f"{remaining_tasks} BACKGROUND TASKS ACTIVE :: {task_name} '{func_name}' completed"
        )
        if remaining_tasks > 5:
            logger.warning(
                f"{remaining_tasks} > 5 BACKGROUND TASKS:: remaining tasks: {[task.get_name() for task in TASKS]}"
            )
        if t.exception():
            logger.error(
                f"BACKGROUND TASK ERROR {task_name} '{func_name}': {t.exception()}"
            )

    task.add_done_callback(cleanup)
    logger.debug(
        f"{len(TASKS)} BACKGROUND TASKS ACTIVE :: {task.get_name()} '{func_name}' started"
    )
    return task
