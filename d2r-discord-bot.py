#!/usr/bin/env python3
"""
A Discord Bot for tracking DClone spawns and Terror Zones in Diablo 2: Resurrected - https://github.com/shallox/d2r-discord-bot

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import asyncio
from datetime import datetime, timedelta
from tools import DbManager
from os import environ, path
from time import time
from requests import get
from discord.ext import tasks
import discord
from discord import SelectOption, Interaction, ButtonStyle, ui
from discord.ui import View, Select, button, Modal, TextInput, Button
from random import randint
from hashlib import md5

#####################
# Bot Configuration #
#####################
# Setting environment variables is preferred, but you can also edit the variables below.

# Discord (Required)
DCLONE_DISCORD_TOKEN = environ.get('DCLONE_DISCORD_TOKEN')
DCLONE_DISCORD_CHANNEL_ID = int(environ.get('DCLONE_DISCORD_CHANNEL_ID'))

# D2RuneWizard API (Optional but recommended)
# This token is necessary for planned walk notifications
DCLONE_D2RW_TOKEN = environ.get('DCLONE_D2RW_TOKEN')

# D2Emu token, required for Terror zoneinfo from D2Emu
DCLONE_D2EMU_TOKEN = environ.get('DCLONE_D2EMU_TOKEN')
print([a for a in environ.keys() if 'DCLONE' in a])
DCLONE_D2EMU_USERNAME = environ.get('DCLONE_D2EMU_USERNAME')

# DClone tracker API (Optional)
# Defaults to All Regions, Ladder and Non-Ladder, Softcore
DCLONE_REGION = environ.get('DCLONE_REGION', '')  # 1 for Americas, 2 for Europe, 3 for Asia, blank for all
DCLONE_LADDER = environ.get('DCLONE_LADDER', '1')  # 1 for Ladder, 2 for Non-Ladder, blank for all
DCLONE_HC = environ.get('DCLONE_HC', '2')  # 1 for Hardcore, 2 for Softcore, blank for all

# Bot specific (Optional)
# Defaults to alerting at level 3 if the last 3 progress reports match
DCLONE_THRESHOLD = int(environ.get('DCLONE_THRESHOLD', 3))  # progress level to alert at (and above)
DCLONE_REPORTS = int(
    environ.get('DCLONE_REPORTS', 3))  # number of matching reports required before alerting (reduces trolling)

# Terror zone list
EVENT_LIST = [
    "Ancient Tunnels",
    "Ancient’s Way and Icy Cellar",
    "Arcane Sanctuary",
    "Arreat Plateau and Pit of Acheron",
    "Black Marsh and The Hole",
    "Blood Moor and Den of Evil",
    "Bloody Foothills, Frigid Highlands, and Abaddon",
    "Burial Grounds, The Crypt, and The Mausoleum",
    "Cathedral and Catacombs",
    "Chaos Sanctuary",
    "Cold Plains and The Cave",
    "Crystalline Passage and Frozen River",
    "Dark Wood and Underground Passage",
    "Dry Hills and Halls of the Dead",
    "Durance of Hate",
    "Flayer Jungle and Flayer Dungeon",
    "Glacial Trail and Drifter Cavern",
    "Great Marsh",
    "Kurast Bazaar, Ruined Temple, and Disused Fane",
    "Lost City, Valley of Snakes, and Claw Viper Temple",
    "Lut Gholein Sewers",
    "Nihlathak’s Temple, Halls of Anguish, Halls of Pain, and Halls of Vaught",
    "Outer Steppes and Plains of Despair",
    "River of Flame and City of the Damned",
    "Rocky Waste and Stony Tomb",
    "Spider Forest and Spider Cavern",
    "Stony Field",
    "Tal Rasha’s Tombs and Tal Rasha’s Chamber",
    "The Forgotten Tower",
    "Travincal",
    "Tristram",
    "Worldstone Keep, Throne of Destruction, and Worldstone Chamber",
    "Dark Wood / Underground Passage",
    "Black Marsh / The Hole",
    "Jail / Barracks",
    "The Pit",
    "Moo Moo Farm",
    "Sewers",
    "Tal Rasha's Tombs",
    "River of Flame / City of the Damned",
    "Bloody Foothills / Frigid Highlands / Abbadon",
    "Glacial Trail / Drifter Cavern",
    "Arreat Plateau / Pit of Acheron",
    "Nihlathak's Temple, Halls of Anguish, Halls of Pain, and Halls of Vaught",
    "Ancient's Way and Icy Cellar",
]

########################
# End of configuration #
########################
__version__ = '0.2a'
REGION = {'1': 'Americas', '2': 'Europe', '3': 'Asia', '': 'All Regions'}
LADDER = {'1': 'Ladder', '2': 'Non-Ladder', '': 'Ladder and Non-Ladder'}
LADDER_RW = {True: 'Ladder', False: 'Non-Ladder'}
HC = {'1': 'Hardcore', '2': 'Softcore', '': 'Hardcore and Softcore'}
HC_RW = {True: 'Hardcore', False: 'Softcore'}
dt_hour_last = None
last_update = None

# DCLONE_DISCORD_TOKEN and DCLONE_DISCORD_CHANNEL_ID are required
if not DCLONE_DISCORD_TOKEN or DCLONE_DISCORD_CHANNEL_ID == 0:
    print('Please set DCLONE_DISCORD_TOKEN and DCLONE_DISCORD_CHANNEL_ID in your environment.')
    exit(1)

if path.isfile('email.txt'):
    efr = open('email.txt', 'r').read()
else:
    with open('email.txt', 'w') as efr_w:
        efr = input('https://d2runewizard.com needs an email in order to authenticate to its api, please enter one:')
        efr_w.write(efr)
headers = {
    "D2R-Contact": efr.replace('\n', ''),
    "D2R-Platform": "Discord",
    "D2R-Repo": "https://github.com/shallox/d2r-discord-bot"
}


def d2emu_request(mode):
    emu_db = DbManager('emu_tz_cache.json')
    tz_cache = emu_db.read_db()
    if not tz_cache or tz_cache['next_terror_time_utc'] < time() or len(tz_cache['next']) == 0:
        data = get(
            'https://d2emu.com/api/v1/tz',
            headers={
                'x-emu-username': DCLONE_D2EMU_USERNAME,
                'x-emu-token': DCLONE_D2EMU_TOKEN
            }
        )
        if data.status_code == 200:
            data_ = data.json()
            emu_db.write_db(data_)
        else:
            data_ = tz_cache
    else:
        data_ = tz_cache
    zone_db = DbManager('zones.json').read_db()
    immunities_filter = {"ph": 'Physical', "l": 'Lightning', "f": 'Fire', "p": 'Poison', 'c': 'Cold', 'm': 'Magic'}
    raw_current_tz = ''.join(f'{zone_db[str(tz)]}, ' for tz in data_['current']).rsplit(', ', 1)[0]
    sp_current_tz = raw_current_tz.split(', ')
    if len(sp_current_tz) > 2:
        fsplit = raw_current_tz.rsplit(', ', 1)
        current_tz = f"{fsplit[0]}, and {fsplit[1]}"
    else:
        current_tz = raw_current_tz
    raw_next_tz = ''.join(f'{zone_db[str(tz)]}, ' for tz in data_['next']).rsplit(', ', 1)[0]
    sp_next_tz = raw_next_tz.split(', ')
    if len(sp_next_tz) > 2:
        nsplit = raw_next_tz.rsplit(', ', 1)
        next_tz = f"{nsplit[0]}, and {nsplit[1]}"
    else:
        next_tz = raw_next_tz
    raw_dataset = {
        'current_tz': current_tz,
        'current_superuniques': ''.join(f'{ub}, ' for ub in data_['current_superuniques']).rsplit(', ', 1)[0],
        'current_num_boss_packs': f"{data_['current_num_boss_packs'][0]}-{data_['current_num_boss_packs'][1]}",
        'current_immunities': ''.join(f'{immunities_filter[im]}, ' for im in data_['current_immunities'] if im in immunities_filter.keys()).rsplit(', ', 1)[0],
        'next_tz': next_tz,
        'next_superuniques': ''.join(f'{ub}, ' for ub in data_['next_superuniques']).rsplit(', ', 1)[0],
        'next_num_boss_packs': f"{data_['current_num_boss_packs'][0]}-{data_['current_num_boss_packs'][1]}",
        'next_immunities': ''.join(f'{immunities_filter[im]}, ' for im in data_['current_immunities'] if im in immunities_filter.keys()).rsplit(', ', 1)[0],
    }
    global last_update
    last_update = datetime.now()
    tz = raw_dataset['current_tz']
    ntz = raw_dataset['next_tz']
    notifications = ''
    if mode == 'auto':
        notifications += 'Your TZ is up:\n'
        tz_db = DbManager(cache_loc='tz-subscriptions.json')
        tz_sub_cache = tz_db.read_db()
        for userid, user_data in tz_sub_cache.items():
            if user_data['notify'] in ['both', 'mention']:
                if tz.split(' ', 1)[0] in [stz.split(' ', 1)[0] for stz in user_data['events']]:
                    notifications += f'<@{int(userid)}> '
            elif user_data['notify'] == 'email':
                pass
    reply = f':skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::\n' \
            f'Current Terror Zone: {tz}\n' \
            f'Super Uniques in TZ: {raw_dataset["current_superuniques"]}\n' \
            f'Boss packs in TZ: {raw_dataset["current_num_boss_packs"]}\n' \
            f'Immunities in TZ: {raw_dataset["current_immunities"]}\n' \
            f'Next Terror Zone: {ntz}\n' \
            f'Super Uniques in next TZ: {raw_dataset["next_superuniques"]}\n' \
            f'Boss packs in next TZ: {raw_dataset["next_num_boss_packs"]}\n' \
            f'Immunities in next TZ: {raw_dataset["next_immunities"]}\n' \
            f'Data courtesy of d2emu.com\n' \
            f':skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::\n' \
            f'{notifications}'
    return reply


class D2RuneWizardClient():
    """
    Interacts with the d2runewizard.com API to get planned walks and terror zones.
    """

    @staticmethod
    def emoji(region='', ladder='', hardcore=''):
        """
        Returns a string of Discord emoji for a given mode.

        :param region: region to get emoji for
        :param ladder: ladder to get emoji for
        :param hardcore: hardcore to get emoji for
        :return: string of Discord emoji
        """
        if region == 'Americas':
            region = ':flag_us:'
        elif region == 'Europe':
            region = ':flag_eu:'
        elif region == 'Asia':
            region = ':flag_kr:'
        elif region == 'TBD':
            region = ':grey_question:'

        if ladder is True:
            ladder = ':ladder:'
        elif ladder is False:
            ladder = ':crossed_swords:'

        if hardcore is True:
            hardcore = ':skull_crossbones:'
        elif hardcore is False:
            hardcore = ':mage:'

        return f'{region} {ladder} {hardcore}'

    @staticmethod
    def dclone_walks(message):
        # get planned walks from d2runewizard.com API
        if DCLONE_D2RW_TOKEN:
            try:
                response = get(
                    f'https://d2runewizard.com/api/diablo-clone-progress/planned-walks?token={DCLONE_D2RW_TOKEN}',
                    headers=headers,
                    timeout=10)
                response.raise_for_status()

                # filter planned walks to configured mode and add relevant ones to the message
                planned_walks = D2RuneWizardClient.filter_walks(response.json().get('walks'))
                if len(planned_walks) > 0:
                    message += '\n\nPlanned Walks:\n'
                    for walk in planned_walks:
                        region = walk.get('region')
                        ladder = walk.get('ladder')
                        hardcore = walk.get('hardcore')
                        timestamp = int(walk.get('timestamp') / 1000)
                        name = walk.get('displayName')
                        emoji = D2RuneWizardClient.emoji(region=region, ladder=ladder, hardcore=hardcore)
                        unconfirmed = ' **[UNCONFIRMED]**' if not walk.get('confirmed') else ''

                        message += f' - {emoji} **{region} {LADDER_RW[ladder]} {HC_RW[hardcore]}** <t:{timestamp}:R> reported by `{name}`{unconfirmed}\n'
                    message += '> Data courtesy of d2runewizard.com'
                else:
                    message += '\n\nPlanned Walks:\nNo planned walks found.'
                return message
            except Exception as err:
                print(f'[ChatOp] D2RuneWizard API Error: {err}')

    @staticmethod
    def filter_walks(walks):
        """
        Returns a filtered list of walks based on the configured mode (region, ladder, hardcore). Region TBD walks are always included.

        :param walks: list of walks
        :return: list of walks filtered to the configured mode
        """
        # filter walks to configured region, includ any region TBD walks
        if DCLONE_REGION == '1':
            walks = [walk for walk in walks if walk.get('region') == 'Americas' or walk.get('region') == 'TBD']
        elif DCLONE_REGION == '2':
            walks = [walk for walk in walks if walk.get('region') == 'Europe' or walk.get('region') == 'TBD']
        elif DCLONE_REGION == '3':
            walks = [walk for walk in walks if walk.get('region') == 'Asia' or walk.get('region') == 'TBD']

        # filter walks to ladder/non-ladder
        if DCLONE_LADDER == '1':
            walks = [walk for walk in walks if walk.get('ladder')]
        elif DCLONE_LADDER == '2':
            walks = [walk for walk in walks if not walk.get('ladder')]

        # filter walks to hardcore/softcore
        if DCLONE_HC == '1':
            walks = [walk for walk in walks if walk.get('hardcore')]
        elif DCLONE_HC == '2':
            walks = [walk for walk in walks if not walk.get('hardcore')]

        return walks

    @staticmethod
    def terror_zone(mode):
        def tz_cache_update(hash__, data):
            tz_cache[hash__] = data
            db_.write_db(tz_cache)

        """
        Returns latest terror zone info.

        :return: string of walk information.
        """
        db_ = DbManager(cache_loc='terrorzone.json')
        tz_cache = db_.read_db()
        terror_zone_data = get(
            f'https://d2runewizard.com/api/terror-zone?token={DCLONE_D2RW_TOKEN}',
            headers=headers,
            timeout=10).json()
        terror_info = dict(terror_zone_data)["currentTerrorZone"]
        next_terror_info = dict(terror_zone_data)['nextTerrorZone']
        tz = terror_info["zone"]
        if tz_cache:
            tz_hash = md5(
                f'{datetime.utcnow().replace(minute=0, second=0, microsecond=0).isoformat()}-{tz}'.encode()).hexdigest()
            if tz_hash is not tz_cache.keys():
                tz_cache_update(tz_hash, {'zone': tz, 'ts': datetime.utcnow().replace(minute=0, second=0,
                                                                                      microsecond=0).isoformat() + "Z"})
        else:
            tz_cache_update(
                md5(f'{datetime.utcnow().replace(minute=0, second=0, microsecond=0).isoformat()}-{tz}'.encode()).hexdigest(),
                {'zone': tz, 'ts': datetime.utcnow().replace(minute=0, second=0, microsecond=0).isoformat() + "Z"})
        ntz = next_terror_info['zone']
        global last_update
        last_update = datetime.now()
        notifications = ''
        if mode == 'auto':
            notifications += 'Your TZ is up:\n'
            tz_db = DbManager(cache_loc='tz-subscriptions.json')
            tz_sub_cache = tz_db.read_db()
            for userid, user_data in tz_sub_cache.items():
                if user_data['notify'] in ['both', 'mention']:
                    if tz.split(' ', 1)[0] in [stz.split(' ', 1)[0] for stz in user_data['events']]:
                        notifications += f'<@{int(userid)}> '
                elif user_data['notify'] == 'email':
                    pass
        reply = f':skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::\n' \
                f'Current Terror Zone: {tz}\n' \
                f'Next Terror Zone: {ntz}\n' \
                f'Data courtesy of d2runewizard.com\n' \
                f':skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::skull_crossbones::\n'\
                f'{notifications}'
        return reply


class Diablo2IOClient():
    """
    Interacts with the diablo2.io dclone API. Tracks the current progress and recent reports for each mode.
    """

    def __init__(self):
        # Current progress (last alerted) for each mode
        self.current_progress = {
            ('1', '1', '1'): 1,  # Americas, Ladder, Hardcore
            ('1', '1', '2'): 1,  # Americas, Ladder, Softcore
            ('1', '2', '1'): 1,  # Americas, Non-Ladder, Hardcore
            ('1', '2', '2'): 1,  # Americas, Non-Ladder, Softcore
            ('2', '1', '1'): 1,  # Europe, Ladder, Hardcore
            ('2', '1', '2'): 1,  # Europe, Ladder, Softcore
            ('2', '2', '1'): 1,  # Europe, Non-Ladder, Hardcore
            ('2', '2', '2'): 1,  # Europe, Non-Ladder, Softcore
            ('3', '1', '1'): 1,  # Asia, Ladder, Hardcore
            ('3', '1', '2'): 1,  # Asia, Ladder, Softcore
            ('3', '2', '1'): 1,  # Asia, Non-Ladder, Hardcore
            ('3', '2', '2'): 1,  # Asia, Non-Ladder, Softcore
        }

        # Recent reports for each mode. These are truncated to DCLONE_REPORTS and alerts are sent if
        # all recent reports for a mode agree on the progress level. This reduces trolling/false reports
        # but also increases the delay between a report and an alert.
        self.report_cache = {
            ('1', '1', '1'): [1],  # Americas, Ladder, Hardcore
            ('1', '1', '2'): [1],  # Americas, Ladder, Softcore
            ('1', '2', '1'): [1],  # Americas, Non-Ladder, Hardcore
            ('1', '2', '2'): [1],  # Americas, Non-Ladder, Softcore
            ('2', '1', '1'): [1],  # Europe, Ladder, Hardcore
            ('2', '1', '2'): [1],  # Europe, Ladder, Softcore
            ('2', '2', '1'): [1],  # Europe, Non-Ladder, Hardcore
            ('2', '2', '2'): [1],  # Europe, Non-Ladder, Softcore
            ('3', '1', '1'): [1],  # Asia, Ladder, Hardcore
            ('3', '1', '2'): [1],  # Asia, Ladder, Softcore
            ('3', '2', '1'): [1],  # Asia, Non-Ladder, Hardcore
            ('3', '2', '2'): [1],  # Asia, Non-Ladder, Softcore
        }

        # tracks planned walks from D2RuneWizard that have already alerted
        # TODO: move to D2RuneWizardClient
        self.alerted_walks = []

    @staticmethod
    def emoji(region='', ladder='', hardcore=''):
        """
        Returns a string of Discord emoji for a given game mode.

        :param region: 1 for Americas, 2 for Europe, 3 for Asia
        :param ladder: 1 for Ladder, 2 for Non-Ladder
        :param hardcore: 1 for Hardcore, 2 for Softcore
        :return: Discord emoji string
        """
        if region == '1':
            region = ':flag_us:'
        elif region == '2':
            region = ':flag_eu:'
        elif region == '3':
            region = ':flag_kr:'

        if ladder == '1':
            ladder = ':ladder:'
        elif ladder == '2':
            ladder = ':crossed_swords:'

        if hardcore == '1':
            hardcore = ':skull_crossbones:'
        elif hardcore == '2':
            hardcore = ':mage:'

        return f'{region} {ladder} {hardcore}'

    def status(self, region='', ladder='', hardcore=''):
        """
        Get the currently reported dclone status from the diablo2.io dclone API.

        API documentation: https://diablo2.io/post2417121.html

        :param region: region to get status for (1 for Americas, 2 for Europe, 3 for Asia, blank for all)
        :param ladder: ladder or non-ladder (1 for Ladder, 2 for Non-Ladder, blank for all)
        :param hardcore: hardcore or softcore (1 for Hardcore, 2 for Softcore, blank for all)
        :return: current dclone status as json
        """
        db = DbManager(cache_loc='dclone.json')
        db_read_cache = db.read_db()
        query_api = False
        if not db_read_cache:
            query_api = True
        elif datetime.utcnow() - datetime.fromisoformat(db_read_cache['ts'].replace("Z", "")) > timedelta(minutes=1):
            query_api = True
        else:
            return_data = db_read_cache['data']
        if query_api:
            url = 'https://diablo2.io/dclone_api.php'
            params = {'region': region, 'ladder': ladder, 'hc': hardcore}
            headers = {'User-Agent': f'dclone-discord/{__version__}'}
            response = get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            db_read_cache['data'] = response.json()
            db_read_cache['ts'] = datetime.utcnow().isoformat() + "Z"
            db.write_db(db_read_cache)
            return_data = response.json()
        return return_data

    def progress_message(self):
        """
        Returns a formatted message of the current dclone status by mode (region, ladder, hardcore).
        """
        # get the currently reported dclone status
        # TODO: return from current_progress instead of querying the API every time?
        status = self.status(region=DCLONE_REGION, ladder=DCLONE_LADDER, hardcore=DCLONE_HC)
        if not status:
            return '[Diablo2IOClient.progress_message] API error, please try again later.'

        # sort the status by mode (hardcore, ladder, region)
        status = sorted(status, key=lambda x: (x['hc'], x['ladder'], x['region']))

        # build the message
        message = 'Current DClone Progress:\n'
        for data in status:
            region = data.get('region')
            ladder = data.get('ladder')
            hardcore = data.get('hc')
            progress = int(data.get('progress'))
            timestamped = int(data.get('timestamped'))
            emoji = Diablo2IOClient.emoji(region=region, ladder=ladder, hardcore=hardcore)

            message += f' - {emoji} **{REGION[region]} {LADDER[ladder]} {HC[hardcore]}** is `{progress}/6` <t:{timestamped}:R>\n'
        message += '> Data courtesy of diablo2.io'
        final_message = D2RuneWizardClient.dclone_walks(message)
        return final_message

    def should_update(self, mode):
        """
        For a given game mode, returns True/False if we should post an alert to Discord.

        This checks for DCLONE_REPORTS number of matching progress reports which is intended to reduce trolling/false reports.
        A larger number for DCLONE_REPORTS will alert sooner (less delay) but is more susceptible to trolling/false reports and
        a smaller number of DCLONE_REPORTS will alert later (more delay) but is less susceptible to trolling/false reports.

        Since we're checking every 60 seconds any mode with the same progress report for 60*DCLONE_REPORTS seconds
        will also be reported as a change.

        :param mode: game mode (region, ladder, hardcore)
        :return: True/False if we should post an alert to Discord
        """
        reports = self.report_cache[mode][-DCLONE_REPORTS:]
        self.report_cache[mode] = reports  # truncate recent reports

        # if the last DCLONE_REPORTS reports agree on the progress level, we should update
        if all(reports[0] == x for x in reports):
            return True

        return False


class EventSubscriptionView(View):
    def __init__(self, user_id: int, events: list[str]):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.events = events

        # Split into pages of ≤25 options
        self.pages = [events[i:i+25] for i in range(0, len(events), 25)]
        self.page = 0
        self.selected: list[str] = []
        self._build_view()

    def _build_view(self):
        self.clear_items()

        # Dropdown for the current page
        opts = [
            SelectOption(label=e, value=e, default=(e in self.selected))
            for e in self.pages[self.page]
        ]
        select = Select(
            placeholder=f"Page {self.page+1}/{len(self.pages)} → pick events",
            min_values=0,
            max_values=len(opts),
            options=opts,
            custom_id=f"event_sel_{self.page}"
        )
        select.callback = self.select_callback
        self.add_item(select)

        # Prev/Next if multiple pages
        if len(self.pages) > 1:
            prev = Button(label="⬅️ Prev", style=ButtonStyle.secondary, custom_id="prev_page")
            nxt = Button(label="Next ➡️", style=ButtonStyle.secondary, custom_id="next_page")
            prev.callback = self.prev_page
            nxt.callback = self.next_page
            self.add_item(prev)
            self.add_item(nxt)

        # Submit button
        submit = Button(label="✅ Submit", style=ButtonStyle.success, custom_id="submit")
        submit.callback = self.submit
        self.add_item(submit)

    async def select_callback(self, interaction: Interaction):
        new_vals = interaction.data.get("values", [])
        # Remove old selections from this page
        for e in self.pages[self.page]:
            if e in self.selected and e not in new_vals:
                self.selected.remove(e)
        # Add any newly selected
        for e in new_vals:
            if e not in self.selected:
                self.selected.append(e)
        await interaction.response.defer(ephemeral=True)

    # Now only takes interaction
    async def prev_page(self, interaction: Interaction):
        self.page = (self.page - 1) % len(self.pages)
        self._build_view()
        await interaction.response.edit_message(view=self)

    # Now only takes interaction
    async def next_page(self, interaction: Interaction):
        self.page = (self.page + 1) % len(self.pages)
        self._build_view()
        await interaction.response.edit_message(view=self)

    # Now only takes interaction
    async def submit(self, interaction: Interaction):
        # Persist final selection
        sub_db = DbManager('tz-subscriptions.json')
        data = sub_db.read_db() or {}
        entry = data.setdefault(str(self.user_id), {})
        entry['events'] = self.selected
        sub_db.write_db(data)

        # Hand off to next step (notification-method view)
        await interaction.response.send_message(
            "Great! How would you like to be notified when those Terror Zones come up?",
            view=NotificationMethodView(self.user_id),
            ephemeral=True
        )
        self.stop()


class NotificationMethodView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @button(label="📧 Email me", style=ButtonStyle.primary, custom_id="notify_email")
    async def email_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(EmailModal(self.user_id, mention=False))
        self.stop()

    @button(label="🔔 Mention me", style=ButtonStyle.secondary, custom_id="notify_mention")
    async def mention_button(self, interaction: Interaction, button: Button):
        sub_db = DbManager('tz-subscriptions.json')
        data = sub_db.read_db() or {}
        entry = data.setdefault(str(self.user_id), {})
        entry['notify'] = 'mention'
        entry['email'] = ''
        sub_db.write_db(data)

        await interaction.response.send_message(
            "✅ You will be mentioned in the channel when your selected Terror Zones come up!",
            ephemeral=True
        )
        self.stop()

    @button(label="✉️🔔 Both", style=ButtonStyle.success, custom_id="notify_both")
    async def both_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(EmailModal(self.user_id, mention=True))
        self.stop()


class EmailModal(Modal, title="Enter your email address"):
    email = TextInput(
        label="Email Address",
        placeholder="you@example.com",
        required=True
    )

    def __init__(self, user_id: int, mention: bool):
        super().__init__()
        self.user_id = user_id
        self.mention = mention

    async def on_submit(self, interaction: Interaction):
        address = self.email.value
        sub_db = DbManager('tz-subscriptions.json')
        data = sub_db.read_db() or {}
        entry = data.setdefault(str(self.user_id), {})
        entry['email'] = address
        entry['notify'] = 'both' if self.mention else 'email'
        sub_db.write_db(data)

        await interaction.response.send_message(
            f"✅ I'll email you at `{address}`" +
            (" and mention you in-channel" if self.mention else "") +
            " when your events occur.",
            ephemeral=True
        )
        self.stop()


class DiscordClient(discord.Client):
    """
    Connects to Discord and starts a background task that checks the diablo2.io dclone API every 60 seconds.
    When a progress change occurs that is greater than or equal to DCLONE_THRESHOLD and for more than DCLONE_REPORTS
    consecutive updates, the bot will send a message to the configured DCLONE_DISCORD_CHANNEL_ID.
    """

    def __init__(self, *args, **kwargs):
        supplied = kwargs.pop("intents", None)
        if supplied is None:
            intents = discord.Intents.default()
        else:
            intents = supplied
        intents.message_content = True
        super().__init__(*args, intents=intents, **kwargs)

        self.dclone = Diablo2IOClient()
        print(f'Tracking DClone for {REGION[DCLONE_REGION]}, {LADDER[DCLONE_LADDER]}, {HC[DCLONE_HC]}')

        # DCLONE_D2RW_TOKEN is required for planned walk notifications
        if not DCLONE_D2RW_TOKEN:
            print('WARNING: DCLONE_D2RW_TOKEN is not set, you will not receive planned walk notifications.')

    async def on_ready(self):
        """
        Runs when the bot is connected to Discord and ready to receive messages. This starts our background task.
        """
        # pylint: disable=no-member
        print(f'Bot logged into Discord as "{self.user}"')
        servers = sorted([g.name for g in self.guilds])
        print(f'Connected to {len(servers)} servers: {", ".join(servers)}')

        # channel details
        channel = self.get_channel(DCLONE_DISCORD_CHANNEL_ID)
        if not channel:
            print('ERROR: Unable to access channel, please check DCLONE_DISCORD_CHANNEL_ID')
            await self.close()
            return
        print(f'Messages will be sent to #{channel.name} on the {channel.guild.name} server')

        # start the background task to monitor dclone status
        try:
            self.check_dclone_status.start()
        except RuntimeError as err:
            print(f'Background Task Error: {err}')

    async def on_message(self, message):
        # don’t respond to other bots (including yourself)
        if message.author.bot:
            return

        channel = message.channel  # simpler than get_channel
        content = message.content

        if content.startswith('!dclonesub'):
            sub_db = DbManager(cache_loc='dclone-subscriptions.json')
            if not sub_db:
                sub_db.write_db({})
            db_data = sub_db.read_db()
            db_data[message.author.name] = message.author.id
            sub_db.write_db(db_data)
            print(f"User {message.author.name} ({message.author.id}) subscribed")
            await channel.send(f"✅ {message.author.mention}, you’re now subscribed.")
        elif content.startswith('!dclone'):
            print(f'Responding to dclone chatop from {message.author}')
            await channel.send(self.dclone.progress_message())
        elif content.startswith('!tzsub'):
            view = EventSubscriptionView(user_id=message.author.id, events=EVENT_LIST)
            await channel.send(
                "Choose what Terror Zones you would like to be notified about:",
                view=view
            )
        elif content.startswith('!tz'):
            print(DCLONE_D2EMU_TOKEN)
            if DCLONE_D2EMU_TOKEN:
                print(f'Providing Terror Zone info to {message.author}')
                await channel.send(d2emu_request(mode='user'))
            elif DCLONE_D2RW_TOKEN:
                print(f'Providing Terror Zone info to {message.author}')
                await channel.send(D2RuneWizardClient.terror_zone(mode='user'))

        elif content.startswith('!roll'):
            parts = content.split()
            try:
                top = int(parts[1]) if len(parts) > 1 else 6
            except ValueError:
                top = 6
            roll = randint(1, top)
            print(f'Providing random roll to {message.author}')
            await channel.send(f'{message.author.mention} rolled: {roll}')
        elif content.startswith('!myid'):
            print(f"User: {message.author.name}, ID: {message.author.id}")
            await channel.send(f"Your Discord ID is `{message.author.id}`")

        elif content.startswith('!help'):
            await channel.send(
                '**Commands**\n'
                '`!dclone` – show current DClone status\n'
                '`!tz` – show Terror Zone info\n'
                '`!roll [n]` – roll 1–n (default 6)\n'
                '`!dclonesub` – subscribe to DClone pings\n'
                '`!tzsub` – pick which random events you want\n'
                '`!myid` – DM your Discord ID\n'
                '`!help` – show this menu'
            )

    @tasks.loop(seconds=60)
    async def check_dclone_status(self):
        """
        Background task that checks dclone status via the diablo2.io dclone public API every 60 seconds.

        Status changes are compared to the last known status and a message is sent to Discord if the status changed.
        """
        # print('>> Checking DClone Status...')
        status = self.dclone.status(region=DCLONE_REGION, ladder=DCLONE_LADDER, hardcore=DCLONE_HC)
        if not status:
            return

        # loop through each region and check for progress changes
        for data in status:
            region = data.get('region')
            ladder = data.get('ladder')
            hardcore = data.get('hc')
            progress = int(data.get('progress'))
            reporter_id = data.get('reporter_id')
            timestamped = int(data.get('timestamped'))
            emoji = Diablo2IOClient.emoji(region=region, ladder=ladder, hardcore=hardcore)

            progress_was = self.dclone.current_progress.get((region, ladder, hardcore))

            # add the most recent report
            self.dclone.report_cache[(region, ladder, hardcore)].append(progress)

            # handle progress changes
            # TODO: bundle multiple changes into one message?
            if int(progress) >= DCLONE_THRESHOLD and progress > progress_was and self.dclone.should_update(
                    (region, ladder, hardcore)):
                print(
                    f'{REGION[region]} {LADDER[ladder]} {HC[hardcore]} is now {progress}/6 (was {progress_was}/6) (reporter_id: {reporter_id})')

                # post to discord
                sub_db_ = DbManager('dclone-subscriptions.json').read_db()
                if sub_db_:
                    user_ids_to_ping = sub_db_.values()
                else:
                    user_ids_to_ping = []
                mentions = ' '.join([f'<@{uid}>' for uid in user_ids_to_ping])
                message = f'[{progress}/6] {emoji} **{REGION[region]} {LADDER[ladder]} {HC[hardcore]}** DClone progressed (reporter_id: {reporter_id})'
                message += '\n> Data courtesy of diablo2.io'

                channel = self.get_channel(DCLONE_DISCORD_CHANNEL_ID)
                await channel.send(f'{message}\n{mentions}')

                # update current status
                self.dclone.current_progress[(region, ladder, hardcore)] = progress
            elif progress < progress_was and self.dclone.should_update((region, ladder, hardcore)):
                # progress increases are interesting, but we also need to reset to 1 after dclone spawns
                # and to roll it back if the new confirmed progress is less than the current progress
                print(
                    f'[RollBack] {REGION[region]} {LADDER[ladder]} {HC[hardcore]} rolling back to {progress} (reporter_id: {reporter_id})')

                # if we believe dclone spawned, post to discord
                if progress == 1:
                    message = ':japanese_ogre: :japanese_ogre: :japanese_ogre: '
                    message += f'[{progress}/6] **{REGION[region]} {LADDER[ladder]} {HC[hardcore]}** DClone may have spawned (reporter_id: {reporter_id})'
                    message += '\n> Data courtesy of diablo2.io'

                    channel = self.get_channel(DCLONE_DISCORD_CHANNEL_ID)
                    await channel.send(message)

                # update current status
                self.dclone.current_progress[(region, ladder, hardcore)] = progress
            elif progress != progress_was:
                # track suspicious progress changes, these are not sent to discord
                report_timestamp = datetime.fromtimestamp(timestamped).strftime('%Y-%m-%d %H:%M:%S')
                print(f'[Suspicious] {REGION[region]} {LADDER[ladder]} {HC[hardcore]} reported as {progress}/6 ' +
                      f'(currently {progress_was}/6) (reporter_id: {reporter_id}) at {report_timestamp}')

        # check for upcoming walks using the D2RuneWizard API
        if DCLONE_D2RW_TOKEN:
            channel = self.get_channel(DCLONE_DISCORD_CHANNEL_ID)
            try:
                response = get(
                    f'https://d2runewizard.com/api/diablo-clone-progress/planned-walks?token={DCLONE_D2RW_TOKEN}',
                    timeout=10)
                response.raise_for_status()

                walks = D2RuneWizardClient.filter_walks(response.json().get('walks'))
                for walk in walks:
                    walk_id = walk.get('id')
                    timestamp = int(walk.get('timestamp') / 1000)
                    walk_in_mins = int(int(timestamp - time()) / 60)

                    # for walks in the next hour, send an alert if we have not already sent one
                    if walk_in_mins <= 60 and walk_id not in self.dclone.alerted_walks:
                        region = walk.get('region')
                        ladder = walk.get('ladder')
                        hardcore = walk.get('hardcore')
                        name = walk.get('displayName')
                        emoji = D2RuneWizardClient.emoji(region=region, ladder=ladder, hardcore=hardcore)
                        unconfirmed = ' [UNCONFIRMED]' if walk.get('unconfirmed') else ''

                        # post to discord
                        print(
                            f'[PlannedWalk] {region} {LADDER_RW[ladder]} {HC_RW[hardcore]} reported by {name} in {walk_in_mins}m {unconfirmed}')
                        message = f'{emoji} Upcoming walk for **{region} {LADDER_RW[ladder]} {HC_RW[hardcore]}** '
                        message += f'starts at <t:{timestamp}:f> (reported by `{name}`){unconfirmed}'
                        message += '\n> Data courtesy of d2runewizard.com'

                        channel = self.get_channel(DCLONE_DISCORD_CHANNEL_ID)
                        await channel.send(message)

                        self.dclone.alerted_walks.append(walk_id)
            except Exception as err:
                print(f'[PlannedWalk] D2RuneWizard API Error: {err}')
            global dt_hour_last
            this_hour = datetime.now()
            if last_update is None:
                dt_hour_last = datetime.now()
                if DCLONE_D2EMU_TOKEN:
                    await channel.send(f'{d2emu_request(mode="auto")}')
                elif DCLONE_D2RW_TOKEN:
                    await channel.send(f'{D2RuneWizardClient.terror_zone(mode="auto")}')
            elif dt_hour_last.hour == this_hour.hour:
                if last_update.hour == this_hour.hour:
                    pass
                else:
                    await asyncio.sleep(160)
                    dt_hour_last = datetime.hour
                    if DCLONE_D2EMU_TOKEN:
                        await channel.send(f'{d2emu_request(mode="auto")}')
                    elif DCLONE_D2RW_TOKEN:
                        await channel.send(f'{D2RuneWizardClient.terror_zone(mode="auto")}')
            elif dt_hour_last != this_hour:
                await asyncio.sleep(160)
                if DCLONE_D2EMU_TOKEN:
                    msg_data = d2emu_request(mode="auto")
                    await channel.send(f'{msg_data}')
                else:
                    msg_data = D2RuneWizardClient.terror_zone(mode="auto")
                    await channel.send(f'{msg_data}')
                if last_update.hour == this_hour.hour:
                    dt_hour_last = datetime.now()
                    await channel.send(f'{msg_data}')
                else:
                    pass

    @check_dclone_status.before_loop
    async def before_check_dclone_status(self):
        """
        Runs before the background task starts. This waits for the bot to connect to Discord and sets the initial dclone status.
        """
        await self.wait_until_ready()  # wait until the bot logs in

        # get the current progress from the dclone API
        status = self.dclone.status(region=DCLONE_REGION, ladder=DCLONE_LADDER, hardcore=DCLONE_HC)

        if not status:
            print('Unable to set the current progress at startup')
            return

        # set the current status and populate the report cache with this value
        # this prevents a duplicate message from being sent when the bot starts
        # we are assuming the report at startup is correct (not a troll/false report)
        # but this should be fine most of the time
        for data in status:
            region = data.get('region')
            ladder = data.get('ladder')
            hardcore = data.get('hc')
            progress = int(data.get('progress'))
            reporter_id = data.get('reporter_id')

            # set current progress and report
            self.dclone.current_progress[(region, ladder, hardcore)] = progress
            if progress != 1:
                print(
                    f'Progress for {REGION[region]} {LADDER[ladder]} {HC[hardcore]} starting at {progress}/6 (reporter_id: {reporter_id})')

            # populate the report cache with DCLONE_REPORTS number of reports at this progress
            for _ in range(0, DCLONE_REPORTS):
                self.dclone.report_cache[(region, ladder, hardcore)].append(progress)


if __name__ == '__main__':
    client = DiscordClient(intents=discord.Intents.default())
    client.run(DCLONE_DISCORD_TOKEN)
