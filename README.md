# mordhau-rcon-suite

This bot is a manual fork of https://github.com/UltimateForm/mordhauTitles


- [mordhau-rcon-suite](#mordhau-rcon-suite)
  - [Usage](#usage)
    - [Setup](#setup)
    - [Example .env](#example-env)
  - [mordhauMigrantTitles](#mordhaumigranttitles)
    - [What it do?](#what-it-do)
    - [Important note](#important-note)
    - [FAQs](#faqs)
  - [mordhauPersistentTitles](#mordhaupersistenttitles)
    - [What it do?](#what-it-do-1)
    - [Playtime Titles](#playtime-titles)
      - [REQUIRED TABLES (COLLECTIONS)](#required-tables-collections)
      - [Ingame features](#ingame-features)
      - [.env Config](#env-config)
      - [FAQ](#faq)
    - [Discord usage](#discord-usage)
      - [Boards](#boards)
    - [Important notes](#important-notes)

## Usage
You need at least Docker installed and a terminal that can run .sh files (linux or unix-like system)

### Setup

1. clone repo or download code
1. create .env file in same folder as code with these parameters:
    1. RCON_PASSWORD
    1. RCON_ADDRESS
    1. RCON_PORT
    3. RCON_CONNECT_TIMEOUT (optional)
    4. DB_NAME
    5. PLAYTIME_CHANNEL (channel to post playtime scoreboard, read more at [boards](#boards))
    6. PLAYTIME_REFRESH_TIME (time interval in seconds for playtime scoreboard update)
    7. D_TOKEN (discord bot auth token)
    8. TITLE (optional)
    9. BOT_CHANNEL (optional id of channel if you want to limit bot use to one channel)
    10. DB_CONNECTION_STRING (optional, for [playtime titles](#playtime-titles))

2. run `sh restart.sh` in terminal
    1. if you're familar with docker or python you don't necessarily need to this, you can run this bot anywhere and however you want

### Example .env
```
RCON_PASSWORD=superD_uprSecurePw
RCON_ADDRESS=192.168.0.52
RCON_PORT=27019
RCON_CONNECT_TIMEOUT=10
D_TOKEN=sNb5gkzmvnJ8W9rxHP23kNV5s7GDwtY4J4cY4JNbbM5Bctd8UFURsv8TAShsPdPDXFcaai2WlPaHy3Rxis5C3m5dHXk1leUU
TITLE=KING
DB_CONNECTION_STRING=mongodb+srv://yourMongoDbUser:yourSafeMongoDbPsw@url.to.mongodb.net
DB_NAME=mordhau
PLAYTIME_CHANNEL=1941542230754205341
PLAYTIME_REFRESH_TIME=1800
```


## mordhauMigrantTitles

### What it do?

This bot, in essence, is a form of encouragement for bloodshed by introducing an unique tag that migrates via kill. Title's name is configurable in .env file. Here below it is further described.

- On a round that just started, given a player of name JohnWick, upon him killing another player of name KevinSpacey, given that is the first kill in the round, JohnWick is awarded title "REX" (his name becomes `[REX] JohnWick`) and server message is spawned:
  > JohnWick has defeated KevinSpacey and claimed the vacant REX title
- On a round where player JohnWick is the current holder of REX title, when he is killed by player DonnieYen, JohnWick's name loses "REX" tag and DonnieYen's name is changed to  `[REX] DonnieYen` and server message is spawned:
  > DonnieYen has defeated [REX] JohnWick and claimed his REX title

### Important note
1. this hasn't been stress tested
   1. I tested on a small server with 20-30 ppl
   2. most of my testing has been on personal local server with bots
2. consider restarting this bot every 2-3 days, long rcon connections can become unpredictable

### FAQs
- How does the first title holder gets selected? (as in when there's no current holder)
  - first killer dectected while title is vacant gets awarded the title
- What happens when current title holder leaves server?
  - title is made vacant, conditions regarding vacant titles apply


## mordhauPersistentTitles

This a Discord X RCON bot that is used to implement persistent tags (via RCON's `renameplayer`) and salutes (via RCON's `say`)

### What it do?

This bot allows you to 
- have custom tags (or titles) in front of player's names, i.e. you can tag a player with name "FFAer" or "Champion". These tags will last until they're removed. **Note that if you add a tag to player while he is ingame he will need to either rejoin server or wait till next round for tag to take effect**
  - the difference between this and the much simpler rcon's `renameplayer` is that this one will persist across sessions, the tag will persist even after player logs out or round ends
- have specific server messages automatically spawn when selected players join server
- permanetly rename player's usernames
- if enabled, have custom [playtime titles](#playtime-titles)

These features are managed via discord

### Playtime Titles
Playtime titles are only enabled once you have a configured MongoDB instance.
Check here for how to get started: https://www.mongodb.com/pricing

Make sure your instance is located geographically close to bot for best performance

#### REQUIRED TABLES (COLLECTIONS)
(If you don't know how to add tables: https://www.mongodb.com/docs/atlas/atlas-ui/collections/)

You will need to at least have 2 tables created for playtime titles:
1. `live_session`: this is where sessions are ephemeraly stored
   1. while ingame users will have records in this table with their login time
   2. when users logout of game session time is calculated and record is deleted
2. `playtime`
   1. this is where playtimes are stored, in minutes

#### Ingame features
- players will have playtime titles appended to their names according to how long they have played on your server
- playtime titles are replaced by titles added via `.addTag PLAYFABID`
- while ingame players can write `.playtime` to obtain their playtimes
- commands
  - `.playtime` shows player's current playtime
  - `.rank` shows player's current and next playtime rank/tag

#### .env Config
1. DB_CONNECTION_STRING (connection string)
   1. this is a connection string for your mongoddb instance, if you are lost please read here: https://www.mongodb.com/docs/guides/atlas/connection-string/
2. DB_NAME (database name)
   1. this is the database, you can create a new one or use any existing one you already have
   2. if you're lost read here https://www.mongodb.com/resources/products/fundamentals/create-database

#### FAQ
1. what is minumum amount of playtime to be recorded?
   1. 1 minute
2. is player's playtime updated in realtime?
   1. no
   2. it's always updated at end of session
3. how is playtime calculated?
   1. upon player joining server:
      1. session record is created in db
      2. this includes login date and time
   2. upon player leaving server:
      1. session record is deleted in db
      2. session time is calculated (logout time - login time)
      3. calculated session time is added to player's total playtime in db
4. can i manually change a player's playtime?
   1. yes
   2. you can do it in mongodb directly
   3. remember that the unit of time is minutes
      1. example db document:
      ```json
      {
        "playfab_id": "TASDK7823KJKJSD7",
        "minutes": 120
      }
      ```

### Discord usage

I will not tell you here how to setup a discord bot, there's already plenty of guides about that. The bot code here does not manage permissions so it's on you to manage the access.

Commands:
- .setTagFormat {tag format}
  - sets the tag format, must always include {0} which is the placeholder for the tag
  - example: `.setTagFormat -{0}-`
- .setSaluteTimer {number of seconds}
  - sets the time in seconds for salute to show up in server,
  - example: `.setSaluteTimer 2`
- .addTag {playfab id} {tag}
  - sets a tag for a playfab id
  - use `*` in place of playfabid to add title for everyone
  - example: `.addTag D98123JKAS78354 CryBaby`
- .addRename {playfab id} {new name}
  - sets a new username for a playfab id
  - example: `.addRename D98123JKAS78354 ChooseABetterName`
- .addPlaytimeTag {time} {tag}
  - sets playtime tag for minimum time played
  - time must be numeric value representing minutes
  - example: `.addPlaytimeTag 300 Veteran`
- .removeTag {playfab id}
  - removes tag for playfabid
  - example: `.removeTag D98123JKAS78354`
- .removeRename {playfab id}
  - removes a rename for playfabid
  - example: `.removeRename D98123JKAS78354`
- .removePlaytimeTag {time}
  - removes a playtime tag
  - example: `.removePlaytimeTag 300`
- .addSalute {playfab id} {salute text}
  - adds salute for playfab id
  - use quotes ("") for multi word salutes
  - example: `.addSalute D98123JKAS78354 "Welcome back Dan"`
- .removeSalute {playfab id}
  - removes salute for playfab id
  - example: `.removeSalute D98123JKAS78354`
- .ptConf
  - shows full config
  - example: `.ptConf`


#### Boards

Configure the bot to send scoreboard by setting the PLAYTIME_CHANNEL variable in .env.

You can additionally configure PLAYTIME_REFRESH_TIME as well to define the time interval for the update, by default it is 60 seconds which corresponds to 1 minute. here are examples for other values:
- 1 hour: 3600
- 30 minutes: 1800
- 1 day: 86400


### Important notes
1. This bot doesn't use (yet) the native discord commands
2. This bot hasn't been stress tested, a previous version has been tested on a server with 20-40 players, but was different code
3. consider restarting this bot every 2-3 days, long rcon connections can become unpredictable