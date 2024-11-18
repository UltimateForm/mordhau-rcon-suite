# this library (asyncio) is for handling asynchronous code execution
import asyncio
from rcon.rcon import RconContext
from rcon.rcon_listener import RconListener
# about the logger, be aware that
# a log file is being written at persist/bot.log
from common import logger, parsers

# place here your RCON stuff like port, password, etc
# BUT! you shouldn't leave it like this, place it here for testing
# but you should be using a more secure way for your RCON credentials
# like for example and .env file, the RCON class will automatically
# try to obtain credentials from environment variables
# if you provide none
rcon_data = {
    "port": 7780,
    "timeout": 10,
    "password": "PASSWORD HERE",
    "address": "ADDRESS.TO.YOUR.SERVER",
}


# this is how you send a command via RCON,
# note the RconContext and asyncio.timeout
# which are asynchronous context managers (https://superfastpython.com/asynchronous-context-manager/);
# with RconContext a new RCON connection is created from scratch
# and diposed after your command is run;
# this is great for containerizing each command;
# check main_with_persistent_connection at rcon/rcon.py
# for how to use with a persistent connection
async def send_command(cmd: str):
    async with asyncio.timeout(10):
        async with RconContext(**rcon_data) as client:
            await client.execute(cmd)


# if you're done event driven programming before you should be familiar with "handlers"
# very simple, the handlers are just the "consumers" of the events
def handle_chat(event_raw: str):
    event = parsers.parse_chat_event(event_raw)
    if not event:
        # probably just the rewarm response
        return
    logger.info(f"Chat from {event.user_name}: {event.message}")
    if event.message.lower() == "hello bot":
        # imagine create_task as a way of starting this in the background;
        # but why create_task? why not just make this method async and await the send_command()
        # this method can't be async because we use it a handler for the listener
        # RxPy default doesnt support async subscribers
        # but there are ways...
        asyncio.create_task(send_command(f"say Hello {event.user_name} :)"))


def handle_killfeed(event_raw: str):
    event = parsers.parse_killfeed_event(event_raw)
    if not event:
        # probably just the rewarm response
        return
    logger.info(f"{event.user_name} killed {event.killed_user_name}")


def handle_login(event_raw: str):
    event = parsers.parse_login_event(event_raw)
    if not event:
        # probably just the rewarm response
        return
    logger.info(f"{event.user_name} logged {event.instance}")


# here we're just creating the listeners
# IMPORTANT: nothing has been started here,
# you're just setting up the listeners, we start them later
login_watcher = RconListener(event="login", **rcon_data)
killfeed_watcher = RconListener(event="killfeed", **rcon_data)
chat_watcher = RconListener(event="chat", **rcon_data)

# here we're subscribing to the listeners
# what do i mean by "subscribe"? https://medium.com/@michamarszaek/reactive-programming-in-python-2af1495c7922
# imagine "subscribe" as an expression of "when X happens I want to do Y"
# where X is the event we're listening and Y are the handlers
login_watcher.subscribe(handle_login)
killfeed_watcher.subscribe(handle_killfeed)
chat_watcher.subscribe(handle_chat)


# this is your entry method, this is where you start all your lifecycle stuff
# like your listeners and any other components that make your bot
async def main():
    logger.use_date_time_logger()
    await asyncio.gather(
        login_watcher.start(), killfeed_watcher.start(), chat_watcher.start()
    )


# this is just to kick off the async event loop
# go read more about asyncio if this confuses you, it's important
asyncio.run(main())
