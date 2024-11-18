# rcon-bot-templates

This is a template project for RCON bots

This was tested on Ubuntu, with python 3.11, but similar versions should work too

Read this and the comments on the code for further insight

## Expected knowledge
1. python 3
2. command line familiarity
3. basic understanding of networks (for RCON)
4. basic understanding of asynchronous programming

## How to run
1. install dependencies
   1. you have many ways to do this but the simplest is `pip install -r ./requirements.txt`
2. change `rcon_data` at `main.py`to fit your server
3. run `python main.py` in command line
4. keep eye on logs

interactions:
- if you say "hello bot" in the game's chat, server should responde with an "hello" as well
- chat messages, killfeed, and login events should be logged on the console
  
## Template structure

```python
.
├── README.md 
├── common
│   ├── logger.py # can delete but you'd need to replace all uses of it with something else
│   ├── models.py
│   └── parsers.py
├── main.py # bot entry point, this most likely where you're gonna be coding
├── persist
│   └── bot.log # created when you run bot
├── rcon # this folder is where the RCON connection is coded, you shouldn't have much to do here
│   ├── rcon.py
│   └── rcon_listener.py
├── requirements.txt # use this to install dependencies, i.e "pip install -r ./requirements.txt"
└── tests
    └── parsers_test.py
```

## Next steps
1. prioritize securing your bot's credentials if you intend to have this code somewhere public, i recommend using an uncommited .env file which can be loaded by https://pypi.org/project/python-dotenv/
2. consider using a virtual environment instead of relying on global packages, here are some tools which can help you with that:
   1. [Poetry](https://python-poetry.org/)
   2. [Pipenv](https://pipenv.pypa.io/en/latest/) 
      1. example: https://github.com/UltimateForm/mordhauTitles
3. consider containerizing the whole bot with something like docker, this way running it becomes more seamless, also easier to run in the background
   1. example dockerfile: https://github.com/UltimateForm/mordhauTitles/blob/master/Dockerfile
   2. example commands: https://github.com/UltimateForm/mordhauTitles/blob/master/restart.sh
4. be mindful of your server's stability while working with RCON which is not very well documented, at worst case a RCON intensive bot can overload a server and cause it to crash
5. get familiar with rcon commands, i recommend using this software https://sourceforge.net/projects/ssrcdsrcon/