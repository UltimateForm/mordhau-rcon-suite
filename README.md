# mordhau-rcon-suite

![botimage](public/rconsuite.png)

This bot is a manual fork of https://github.com/UltimateForm/mordhauTitles which adds the following new features:
- recording kills
  - and broadcasting killstreaks
- sending scoreboards to discord
  - kills
    - including seasonal leaderboards
    - including achievements
  - playtime
  - checking individual player playtime, killscore, and lifetime match score against another player
- player list/server info
- chat logs
  - discord notification when someone includes "@admin" in the chat
  - bi-directional, `.say` command to send chat form discord into game

If you need custom changes please reach out to me on discord or create an issue.

## Contents

- [mordhau-rcon-suite](#mordhau-rcon-suite)
  - [Contents](#contents)
  - [Setup](#setup)
    - [1. clone repo or download code](#1-clone-repo-or-download-code)
    - [2. configure](#2-configure)
      - [a) via .env](#a-via-env)
        - [example](#example)
      - [b) via `./persist/bot.config.json`](#b-via-persistbotconfigjson)
        - [example](#example-1)
      - [Experimental settings](#experimental-settings)
    - [3. setup MONGODB TABLES (COLLECTIONS)](#3-setup-mongodb-tables-collections)
    - [4. run bot](#4-run-bot)
  - [Killstreaks](#killstreaks)
    - [Configuration](#configuration)
      - [example](#example-2)
    - [FAQs](#faqs)
  - [mordhauMigrantTitles](#mordhaumigranttitles)
    - [What it do?](#what-it-do)
    - [Important note](#important-note)
    - [FAQs](#faqs-1)
  - [mordhauPersistentTitles](#mordhaupersistenttitles)
    - [What it do?](#what-it-do-1)
    - [Playtime Titles](#playtime-titles)
      - [Ingame features](#ingame-features)
      - [.env Config](#env-config)
      - [FAQ](#faq)
  - [Chat logs](#chat-logs)
  - [Ingame commands](#ingame-commands)
  - [Discord usage](#discord-usage)
    - [Commands](#commands)
      - [Admin Persistent titles config (.pt)](#admin-persistent-titles-config-pt)
      - [Admin Boards config commands (.boards)](#admin-boards-config-commands-boards)
      - [Admin Db config commands (.db)](#admin-db-config-commands-db)
      - [Admin Season config commands (.season)](#admin-season-config-commands-season)
    - [Boards](#boards)
      - [Playtime records](#playtime-records)
      - [Kill records](#kill-records)
        - [Seasonal kill records](#seasonal-kill-records)
  - [IMPORTANT NOTES](#important-notes)

## Setup
You need at least Docker installed and a terminal that can run .sh files (linux or unix-like system)


### 1. clone repo or download code

Clone this repo or download the code into your working folder. This should be fairly simple, if unsure just google it.

### 2. configure

There are two ways to configure this bot, the .env file described in the previous section and a bot.config.json created in path `./persist/bot.config.json`.

Here's how the config is loaded:
1. check if `./persist/bot.config.json` exists
   1. if yes, load config from that file
   2. if no, load config from environment variables (i.e. .env)
      1. if no settings found in environment variables, create a `./persist/bot.config.json` with default values (**THIS WILL NOT WORK FOR BOT EXECUTION**)

#### a) via .env

- create .env file in same folder as code with these parameters
    1. RCON_PASSWORD
    2. RCON_ADDRESS
    3. RCON_PORT
    4. RCON_CONNECT_TIMEOUT (optional)
    5. DB_NAME
    6. PLAYTIME_CHANNEL (optional, channel to post playtime scoreboard, read more at [boards](#boards))
    7. PLAYTIME_REFRESH_TIME (optional, time interval in seconds for playtime scoreboard update)
    8. KILLS_CHANNEL (optional, channel to post kills/death/ratio scoreboard, read more at [boards](#boards))
    9. KILLS_REFRESH_TIME (optional, time interval in seconds for kills/death/ratio scoreboard update)
    10. INFO_CHANNEL (optional, channel to post server info)
    11. INFO_REFRESH_TIME (optional, time in seconds to refresh server info card)
    12. D_TOKEN (discord bot auth token)
    13. TITLE (optional)
    14. CONFIG_BOT_CHANNEL (id of channel to limit config commands to one channel, only applies to admin commands, check [this section](#commands))
    15. DB_CONNECTION_STRING (for [playtime titles](#playtime-titles) and kill records)
    16. EMBED_FOOTER_TXT (optional, line to add to footer of all embeds, by default it is source code repo link)
    17. EMBED_FOOTER_ICON (optional, link to image to be added at footer of embed)
    18. KS_ENABLED (optional, 1 for enabled, 0 for disabled, default disabled)
    19. CHAT_LOGS_CHANNEL (optional, channel to post chat logs)
    20. EXPERIMENTAL_BULK_LISTENER (optional, 1 for enabled, 0 for disabled)

##### example

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
KILLS_CHANNEL=1213542630756065341
KILLS_REFRESH_TIME=1800
```


  
#### b) via `./persist/bot.config.json`

Create a file with name `bot.config.json` at folder `./persist/` and paste there the template provided below. Replace the square brackets and their content within with actual config values:

- for type number: write just the raw numeric value
- for type string: write the text value between quotes (i.e. `"example"`)
- for type bool: write either `false` or `true`

Template:

```
{
  "info_channel": <type number, optional, channel to post server info>,
  "embed_footer_txt": <type string, optional, channel to post server info>,
  "embed_footer_icon": <type string, optional, link to image to be added at footer of embed>,
  "kills_channel": <type number, channel to post kills/death/ratio scoreboard, read more at #boards>,
  "playtime_channel": <type number, channel to post playtime scoreboard, read more at #boards>,
  "chat_logs_channel": <type number, channel to post chat logs>,
  "playtime_refresh_time": <type number, time interval in seconds for playtime scoreboard update>,
  "kills_refresh_time": <type number, time interval in seconds for kills/death/ratio scoreboard update>,
  "info_refresh_time": <type, optional, time in seconds to refresh server info card>,
  "ks_enabled": <type bool, optional, true for enabled, false for disabled, default disabled>,
  "config_bot_channel": <type number, id of channel to limit config commands to one channel, only applies to commands from #config-commands>,
  "rcon_password": <type string>,
  "rcon_address": <type string>,
  "rcon_port": <type number>,
  "rcon_connect_timeout": <type number, optional, units in seconds>,
  "d_token": <type string, discord bot auth token>,
  "title": <type string, optional, title for migrant titles>,
  "db_connection_string": <type string, for #playtime-titles and kill records>,
  "db_name": <type string, name of the DB you created on dynamodb>
}
```

##### example

```json
{
  "info_channel": 63860684619200738927,
  "embed_footer_txt": "Bot source code: https://github.com/UltimateForm/mordhau-rcon-suite",
  "embed_footer_icon": "https://img.icons8.com/ios-glyphs/1x/github.png",
  "kills_channel": 8975849891383335326,
  "playtime_channel": 1245309379415084945,
  "playtime_refresh_time": 1800,
  "kills_refresh_time": 1800,
  "info_refresh_time": 10,
  "ks_enabled": true,
  "config_bot_channel": 5647207162853061246,
  "rcon_password": "bababoey",
  "rcon_address": "169.159.1.255",
  "rcon_port": 7779,
  "rcon_connect_timeout": 10,
  "d_token": "dffdfsdfsdfsdfsdfwelkhLKJHAKSJDHASKJDASTDL.jokshydiausdhasdaiowe2DF",
  "title": "KING",
  "db_connection_string": "mongodb+srv://yourMongoDbUser:yourSafeMongoDbPsw@url.to.mongodb.net",
  "db_name": "mordhau"
}
```

#### Experimental settings

- EXPERIMENTAL_BULK_LISTENER (json `experimental_bulk_listener`)
  - by default the bot will create different RCON connections per each event it's listening, with this setting enabled the bot will instead reuse the same connection for all the events it needs

### 3. setup MONGODB TABLES (COLLECTIONS)
(If you don't know how to add tables: https://www.mongodb.com/docs/atlas/atlas-ui/collections/)

You will need to at least have 2 tables created for playtime titles:
1. `live_session`: this is where sessions are ephemeraly stored
   1. while ingame users will have records in this table with their login time
   2. when users logout of game session time is calculated and record is deleted
2. `playtime`
   1. this is where playtimes are stored, in minutes
3. `kills`
   1. this is where kill records are stored

### 4. run bot

Run `sh restart.sh` in terminal. Don't worry about that name, it's called "restart" because it will try to stop the bot first if it's running already.

If you're familar with docker or python you don't necessarily need to this, you can run this bot anywhere and however you want

## Killstreaks

If you have killstreaks enabled (see [configuration section](#2-configure)) the bot will broadcast killstreaks to your server. I.e. when a player kills 10 others in a row a server message will say "X has downed 10 foes in a row!". This message is configurable.

### Configuration

For killstreaks to work you need to create a file named `ks.config.json` at folder `./persist/`. Use this template:
```
{
  "streak": {
    "5": [
      <type string, this is a list of template messages for killstreaks>,
      <type string, if you declare an entry this way the bot will select a random killstreak message template in the list>
    ],
    "10": <type string, if you declare it this way, the killstreak template message for 10 kills will always be the same>,
    "15": <type string, note that the template entries must be multiples of 5>,
    "16": THIS WILL NOT WORK, NOT A MULTIPLE OF 5, DELETE THIS LINE
    "20": <type string, template strings support 3 placeholders, {0} for the killer's name, {1} for current kill count, {2} for the killed player's name, see the example below>,
    "25": "{2} is the 25th foe to fall to {0}'s rampage! THEY'RE UNSTOPABLE"
    "*": <type string, this is the global template to be used for any non defined streak, i.e 30, 35, etc>
  },
  "end": {
    "*": <type string, same rules as the streak templates apply here, difference is that these are the templates for when someone's streak is ended>
  },
  "firstblood": <type string, template for the firstblood in a round, same rules apply>
}
```

#### example
```json
{
  "streak": {
    "5": [
      "{0} is on a 5+ kill streak!",
      "HEADS ROLLING! {0} HAS DOWNED 5 FOES IN A ROW"
    ],
    "10": [
      "{0} is on a 10+ kill streak!",
      "{0} IS UNSTOPPABLE! 10 KILLS IN A ROW"
    ],
    "15": "15 CONSECUTIVE KILLS BY {0}!",
    "20": "20?! 20 (!!!) CONSECUTIVE KILLS BY {0}",
    "*": "INSANE {1} CONSECUTIVE KILLSTREAK BY {0}!"
  },
  "end": {
    "10": "bummer, {2}'s killstreak of {1} ended by {0}",
    "*": "{0} ended {2}'s killstreak of {1}",
  },
  "firstblood": "{0} has claimed first blood!"
}
```

### FAQs

- how do i skip a level in the killstreaks? I don't people with just 5 streaks to broadcast killstreak
  - declare the entry with empty value, i.e. `"5": ""` this way no message will be broadcast. If you just don't declare anything for that level then the global (`"*": ...`) template will be used.
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

#### Ingame features
- players will have playtime titles appended to their names according to how long they have played on your server
- playtime titles are replaced by titles added via `.addTag PLAYFABID`

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

## Chat logs

NOTE: you can already have mordhau chat logs sent to your server via [the native webhooks](https://mordhau.fandom.com/wiki/Server_Configuration#Webhooks), so consider this just an alternative.

If you have the setting chat logs enabled (refer back to [configuration chapter](#2-configure)) the bot will be sending chat logs to your discord server. The chat logs look like this:
`ultimate form (TASDK7823KJKJSD7): hello discord`. The playfab id will be a link to [mordhau scribe](https://mordhau-scribe.com/) with info about the player.

If someone writes @admin as part of their chat message the bot will mention @here in the discord channel.

Check [commands](#commands) for how to use the `say` command which will send messages from discord into game.


## Ingame commands

- .playtime
  - will show sender's playtime
- .rank
  - will show sender's playtime rank
- .kdr
  - will show sender's playtime kdr (kill, death, ratio)
- .versus {playfab id or username of another player}
  - will show sender lifetime match state against another player
  - example: `.versus ocelot`
  - DOT NOT CONFUSE WITH THE DISCORD COMMAND WHICH REQUIRES AN ADDITIONAL ARGUMENT.


## Discord usage 

I will not tell you here how to setup a discord bot, there's already plenty of guides about that. The bot code here does not manage permissions so it's on you to manage the access.

### Commands

- **playtime**: gets playtime score for player
  - usage: `.playtime <playfab_id_or_username>`
- **playerlist**: shows online players list
- **skdr**: gets current seasion kdr score for player
  - usage: `.skdr <playfab_id_or_username>`
- **db**: DB admin commands
- **pt**: Persitent titles config commands
- **boards**: Boards admin commands
- **kdr**: gets kdr score for player
  - usage: `.kdr <playfab_id_or_username>`
- **kills**: shows players killed by arg player, use commands such as .kdr or .playtime to obtain playfab id if needed
  - usage: `.kills <playfab_id>`
- **season**: Season admin commands
- **help**: get help about a command, or use without any command to get help about all commands
  - usage: `.help <optional_command>`
- **versus**: shows battle tally between two players, as in how many times they've killed each other
  - usage: `.versus <playfab_id_or_username> <playfab_id_or_username>`
- **say**: send message to ingame chat (this command will only work in the chat_logs channel)
  - usage: `.say <message>`
  - example: `.say ay yo, it's ya boi from discord comming at you with a new message`

#### Admin Persistent titles config (.pt)

- **addPlaytimeTag**: sets playtime title for minimum time played, time must be numeric value representing minutes
  - usage: `.pt addPlaytimeTag <min_time> <title>`
  - example: `.pt addPlaytimeTag 300 Veteran`
- **addTag**: adds a persistant player title, use quotes for titles that include spaces, use * in place of playfabid to add title for everyone
  - usage: `.pt addTag <playfab_id> <title>`
  - example: `.pt addTag D98123JKAS78354 CryBaby`
- **removeRename**: removes a rename for playfabid
  - usage: `.pt removeRename <playfab_id>`
  - example: `.pt removeRename D98123JKAS78354`
- **addSalute**: adds salute for playfab id
  - usage: `.pt addSalute <playfab_id> <salute_txt>`
  - example: `.pt addSalute D98123JKAS78354 "Welcome back Dan"`
- **removeSalute**: removes salute for playfab id
  - usage: `.pt removeSalute <playfab_id>`
  - example: `.pt removeSalute D98123JKAS78354`
- **addRename**: sets a new username for a playfab id
  - usage: `.pt addRename <playfab_id> <new_name>`
  - example: `.pt addRename D98123JKAS78354 ChooseABetterName`
- **removeTag**: removes tag for playfabid
  - usage: `.pt removeTag <min_time>`
  - example: `.pt removeTag 300`
- **ptConf**: show the persistent titles config
- **setSaluteTimer**: sets the time in seconds for salute to show up in server
  - usage: `.pt setSaluteTimer <arg_timer>`
- **removePlaytimeTag**: removes a playtime tag
  - usage: `.pt removePlaytimeTag <min_time>`
  - example: `.pt removePlaytimeTag 300`
- **setTagFormat**: sets the tag format, must always include {0} which is the placeholder for the tag
  - usage: `.pt setTagFormat <format>`
  - example: `.pt setTagFormat -{0}-`

#### Admin Boards config commands (.boards)

- **board_reset**: resets a board, will delete current board message and send a new one, identify the boards by the names InfoBoard, KillsScoreboard, PlayTimeScoreboard
  - usage: `.boards board_reset <board_name>`
- **announce**: set an announcement to be shown in a sent board, identify the boards by the names InfoBoard, KillsScoreboard, PlayTimeScoreboard
  - usage: `.boards announce <board_name> <announcement>`

#### Admin Db config commands (.db)

- **chg_name**: change a player's name in DB
  - usage: `.db chg_name <plafayb_id> <new_name>`
- **metadata**: show metadata of db


#### Admin Season config commands (.season)

- **channel_id**: set channel (by id) to send season score board
  - usage: `.season channel_id <channel_id>`
  - example: `.season channel_id 2912891271860`
- **delete**: delete configured season
- **info**: get info about current configured season
- **create**: create season, currently only supported season_type is `kdr`, name should not have spaces 
  - usage: `.season create <season_type> <name>`
  - example: `.season create kdr Winter2022`
- **end**: end configured season
- **embed**: customize embed fields, the allowed fields are title, description, image_url, footer_txt
  - usage: `.season embed <field> <value>`
  - example: `.season embed title "Winter 2022!"`
- **include**: include players in season
  - usage: `.season include <playfab_id_1> <playfab_id_2> <playfab_id_3> <...etc>`
  - example: `.season include BB50E7E5B75300F6 AB07435720F6A3`
- **start**: start configured season, will error out if not ready to start
- **exclude**: exclude players from season, will not remove already accounted score
  - usage: `.season exclude <playfab_id_1> <playfab_id_2> <playfab_id_3> <...etc>`
  - example: `.season exclude BB50E7E5B75300F6 AB07435720F6A3`


### Boards


#### Playtime records

Configure the bot to send scoreboard by setting the PLAYTIME_CHANNEL variable in .env.

You can additionally configure PLAYTIME_REFRESH_TIME as well to define the time interval for the update, by default it is 60 seconds which corresponds to 1 minute. here are examples for other values:
- 1 hour: 3600
- 30 minutes: 1800
- 1 day: 86400

Example board with random usernames:
```
╔══════════════════════════════════════╗
║ Rank       Username          Time    ║
╟──────────────────────────────────────╢
║  1     8405a755c348fa4e    4.3 hours ║
║  2     9c6889583047dea2     2 hours  ║
║  3     5eb7fee0d776dc19    1.1 hours ║
║  4     1f1aafc1ce0cddec     20 mins  ║
╚══════════════════════════════════════╝
```

#### Kill records

Configure the bot to send kils records by setting the KILLS_CHANNEL variable in .env.

You can additionally configure KILLS_REFRESH_TIME as well to define the time interval for the update, by default it is 60 seconds which corresponds to 1 minute. here are examples for other values:
- 1 hour: 3600
- 30 minutes: 1800
- 1 day: 86400

Example board with random usernames:
```
╔════════════════════════════════════════════════════╗
║ Rank            Username            K    D     R   ║
╟────────────────────────────────────────────────────╢
║  1          6f556ec20719e801        58   8    7.25 ║
║  2          c6d33b6b54c92def        23   12   1.92 ║
║  3          f954c2dd45f76295        22   11   2.0  ║
╚════════════════════════════════════════════════════╝
```

##### Seasonal kill records

The default kdr boards is a persistent one which might leave new players out of board forever unless older players stop playing. To keep the competition fresh you can add seasonal leaderboards have limited time and start counting from 0. Below are the steps for configring a season.

## IMPORTANT NOTES
1. This bot doesn't use (yet) the native discord commands
2. This bot hasn't been stress tested, a previous version has been tested on a server with 20-40 players, but was different code
3. consider restarting this bot every 2-3 days, long rcon connections can become unpredictable
4. this BOT is RCON intensive, expect abnormalities if you have other RCON bots running at same time as this one during resource expensive periods (i.e. 40+ players)
5. CPU usage problems have been reported for this bot, refrain from using this if your CPU is weak
6. Abitrary values on RconTimeout in Game.ini will result in umpredictable RconIssues, you're advised to change it to a standard value i.e. RconTimeout=120.000000 (this one is known to work)
