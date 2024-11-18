FROM python:3.11.3

WORKDIR /bot

COPY ./Pipfile .

COPY ./.env .
     
RUN pip install pipenv

RUN pipenv install

ADD ./common/* ./common

ADD ./config_client/* ./config_client

ADD ./migrant_titles/* ./migrant_titles

ADD ./persistent_titles/* ./persistent_titles

ADD ./rcon/* ./rcon

COPY ./main.py ./

CMD ["pipenv", "run", "python", "main.py"]
