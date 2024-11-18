docker stop mh-rcon-battle-eye
docker rm mh-rcon-battle-eye
docker build . -t mh-rcon-battle-eye-img
docker run -d -v ./persist/:/bot/persist/ --name mh-rcon-battle-eye mh-rcon-battle-eye-img
