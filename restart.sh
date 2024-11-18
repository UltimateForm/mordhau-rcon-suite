docker stop mh-rcon-suite
docker rm mh-rcon-suite
docker build . -t mh-rcon-suite-img
docker run -d -v ./persist/:/bot/persist/ --name mh-rcon-suite mh-rcon-suite-img
