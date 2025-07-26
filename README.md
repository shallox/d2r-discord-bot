# d2r-discord-bot

![](https://img.shields.io/badge/version-1.0.0-blue)

A Discord bot for reporting [DClone Tracker](https://diablo2.io/dclonetracker.php) progress changes, upcoming [planned walks](https://d2runewizard.com/diablo-clone-tracker#planned-walks) and [Terror Zone](https://d2runewizard.com/api/terror-zone) info for Diablo 2: Resurrected. By default, it will report any progress changes at or above level 2 for All Regions, Ladder and Non-Ladder, Softcore and planned walks an hour before they start. Also, every hour it will report on the latest Terror Zone.

You can also get a list of available commands by typing !help in the chat.

You can now use !dclonesub and !tzsub to subscribe and get @mentions when a given TZ comes up or a Dclone walk is imminent. Working on an email system to be updated soon.

## Usage

Requires Python 3.11+, tested on Ubuntu 24.04 and Windows 11.

### Installation

```
git clone https://github.com/shallox/d2r-discord-bot
cd d2r-discord-bot
pip3 install -r requirements.txt
```

### Configuration

Configuration is done via environment variables, or you can edit the variables near the top of the script.

**Required**
 - `DCLONE_DISCORD_TOKEN`: Token for connecting to Discord, create a bot account with the instructions [here](https://discordpy.readthedocs.io/en/stable/discord.html). Only the `Send Messages` permission is required.
 - `DCLONE_DISCORD_CHANNEL_ID`: The [channel id](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-) to send messages to.

**Optional**
 - `DCLONE_D2EMU_TOKEN` (**Highly Recommended**): Token for querying d2emu.com, extreamly detailed terror zone info as well as higher accuracy than d2runwizard - will default to d2emu if a token and username is provided. Request token from the d2emu discord [here](https://discord.gg/yeFkxYdpru)
 - `DCLONE_D2RW_TOKEN`  (**Highly Recommended**): Token for querying d2runewizard.com, required if you want planned walk information as well as terror zone information. Request one [here](https://d2runewizard.com/integration).
 - `TERRORZONE_CHANNEL_ID` Set a channel ID for Terror Zone updates, can be left blank and the Dclone channel will be used instead.
 - `DCLONE_REGION`: `1` for Americas, `2` for Europe, `3` for Asia, blank **(Default)** for All Regions.
 - `DCLONE_LADDER`: `1` for Ladder, `2` for Non-Ladder, blank **(Default)** for both.
 - `DCLONE_HC`: `1` for Harcore, `2` for Softcore **(Default)**, blank for both.
 - `DCLONE_THRESHOLD`: Progress level to report at (and above). Default is 3.
 - `DCLONE_REPORTS`: Only report changes after this many reports agree on a change. Default is 3.

### Running

Start the bot with `python3 d2r-discord-bot.py`.

## Disclaimer

Data courtesy of [diablo2.io](https://diablo2.io), [d2runewizard.com](https://d2runewizard.com) and [d2emu.com](d2emu.com).

Base code courtesy of [Synse](https://github.com/Synse/dclone-discord).
