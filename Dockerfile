FROM python:3.11.3

WORKDIR /bot

COPY ./Pipfile .

COPY ./.env* .

RUN pip install pipenv

RUN pipenv install

ADD ./common/* ./common

ADD ./boards/* ./boards

ADD ./db_kills/* ./db_kills

ADD ./database/* ./database

ADD ./ingame_cmd/* ./ingame_cmd

ADD ./rank_compute/* ./rank_compute

ADD ./config_client/* ./config_client

ADD ./migrant_titles/* ./migrant_titles

ADD ./persistent_titles/* ./persistent_titles

ADD ./rcon/* ./rcon

ADD ./monitoring/* ./monitoring

ADD ./dc_player_commands/* ./dc_player_commands 

ADD ./killstreaks/* ./killstreaks

ADD ./seasons/* ./seasons

ADD ./main.py ./

ADD ./dc_db_config/* ./dc_db_config

CMD ["pipenv", "run", "python", "-u", "main.py"]
