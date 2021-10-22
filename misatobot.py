#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 27 11:34:26 2021

@author: rmoctezuma
"""

import nextcord
from datetime import datetime
from nextcord.team import Team
from nextcord.utils import get
import pytz
from dotenv import load_dotenv
import os
import pandas as pd
import gspread
import gspread_dataframe as gd
from oauth2client.service_account import ServiceAccountCredentials
import json

# Start the BOT!
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
GOOGLE_KEYS = json.loads(os.getenv('GOOGLE_KEYS'))

intents = nextcord.Intents.default()
intents.members = True
intents.presences = True

client = nextcord.Client(intents=intents)

print(datetime.now())

def get_worksheet(worksheet_name):
    gclient = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_KEYS))
    worksheet = gclient.open('WACB5 Battle Log v3.6 - Leads Report').worksheet(worksheet_name)
    ws_df = gd.get_as_dataframe(worksheet, evaluate_formulas=True)
    return worksheet, ws_df

def get_sheet_as_df():
    #scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_KEYS)
    gclient = gspread.authorize(creds)
    worksheet = gclient.open("WACB5 Battle Log v3.6 - Leads Report").worksheet('Battle Log')
    ws_df = gd.get_as_dataframe(worksheet, evaluate_formulas=True)
    return worksheet, ws_df

def file_log(attacker, team, damage):
    worksheet, ws_df=get_worksheet('Battle Log')
    ws_df.rename(columns={"Unnamed: 2": "Boss", "Unnamed: 5": "Attacker"}, inplace=True)
    target_row=0
    for index, row in ws_df.iterrows():
        if not(pd.isna(row['Boss'])) and pd.isna(row['Attacker']) and (index>1):
            target_row = index+2
            break
    if target_row > 0:
        worksheet.update('F' + str(target_row), attacker)
        worksheet.update('G' + str(target_row), team)
        worksheet.update('H' + str(target_row), damage)

def check_boss_status():
    worksheet, ws_df = get_worksheet('Battle Log')
    ws_df.columns = ws_df.iloc[0,:]
    boss=lap=health=0
    for index, row in ws_df.iterrows():
        # print(f"Checking row {index}, columns have [{row['Lap']}] and [{row['Boss']}] and [{row['Health']}]")
        if not(pd.isna(row['Lap'])) and not(pd.isna(row['Boss'])) and not(pd.isna(ws_df.iloc[index-1]['Health'])) and (index>0) and (row['Boss'] != '-'):
            boss=row['Boss']
            lap=row['Lap']
            health=ws_df.iloc[index-1]['Health']
    return (boss, lap, health)

def remaining_teams(team,day):
    worksheet, df = get_worksheet('Battle Log')
    # get all players
    player_df = df.iloc[1:31,[17]]
    player_df.columns = ['IGN']
    player_set = set(player_df['IGN'])
    players_w_id = df.iloc[1:31,[17,18]]
    players_w_id.columns = ['IGN','Discord_ID']
    players_w_id['Discord_ID'] = players_w_id['Discord_ID'].apply(lambda x: x[2:-1])

    # get all attackers
    df = df.iloc[:,[0,5,6]]
    df.columns = ['Day','Attacker','Team']
    df = df[(df['Team'] == team) & (df['Day'] == int(day))]
    attacker_set = set(df['Attacker'])
    
    remaining = list(player_set - attacker_set)
    players_w_id = players_w_id[players_w_id['IGN'].isin(remaining)]
    print(players_w_id)

    return players_w_id

def get_day():
    now = datetime.now()
    if (now.day == 20 and now.hour >= 8) or (now.day == 21 and now.hour < 8):
        day = 1
    elif (now.day == 21 and now.hour >= 8) or (now.day == 22 and now.hour < 8):
        day = 2
    elif (now.day == 22 and now.hour >= 8) or (now.day == 23 and now.hour < 8):
        day = 3
    elif (now.day == 23 and now.hour >= 8) or (now.day == 24 and now.hour < 8):
        day = 4
    elif (now.day == 24 and now.hour >= 8) or (now.day == 25 and now.hour < 8):
        day = 5
    return(day)

# Define a simple View that gives us a confirmation menu
class confirmview(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    @nextcord.ui.button(label='Confirm', style=nextcord.ButtonStyle.green)
    async def confirm(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @nextcord.ui.button(label='Cancel', style=nextcord.ButtonStyle.grey)
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        self.value = False
        self.stop()

@client.event
async def on_ready():
    print('ready to go')

@client.event
async def on_interaction(interaction):
    print(interaction.type)
    if interaction.type == nextcord.InteractionType.application_command:
        name = interaction.data['name']

        if name == 'log':
            await interaction.response.defer()

            status = check_boss_status()
            text = '> Log an attack from {} using {} on Lap {} Boss {} with {} damage?'.format(interaction.data['options'][0]['value'], interaction.data['options'][1]['value'], status[1], status[0], interaction.data['options'][2]['value'])
            view = confirmview()

            await interaction.edit_original_message(content = text, view = view)
            await view.wait()
            if view.value is None:
                await interaction.edit_original_message(content = '> Timed out.', view = None)
            elif view.value:
                boss_dict = {1:'https://static.wikia.nocookie.net/princess-connect/images/c/c1/Wyvern.png/revision/latest/scale-to-width-down/121?cb=20181125033728',2:'https://static.wikia.nocookie.net/princess-connect/images/8/8a/WildGriffon.png/revision/latest/scale-to-width-down/121?cb=20181125034631',3:'https://static.wikia.nocookie.net/princess-connect/images/f/f9/Megalapan.jpg/revision/latest/scale-to-width-down/500?cb=20181125035320',4:'https://static.wikia.nocookie.net/princess-connect/images/4/47/SpiritHorn.png/revision/latest/scale-to-width-down/126?cb=20181125035617',5:'https://static.wikia.nocookie.net/princess-connect/images/0/02/SagittariusBoss.jpg/revision/latest/scale-to-width-down/500?cb=20181125040010'}
                embed = nextcord.Embed(title="Priconne Damage Logging", colour=nextcord.Colour.random(), description="__**Attacker:**__ {}\n__**Team:**__ {}\n__**Lap:**__ {}\n__**Boss:**__ {}\n__**Damage**:__ {}".format(interaction.data['options'][0]['value'], interaction.data['options'][1]['value'], status[1], status[0], interaction.data['options'][2]['value']), timestamp=pytz.utc.localize(datetime.utcnow()).astimezone(pytz.timezone('US/Eastern')))
                embed.set_author(name="Misato Bot", url="https://discordapp.com", icon_url="https://cdn.discordapp.com/avatars/892079008857096253/f749c788d86c481e26096319eae36bc1.png?size=256")
                embed.set_footer(text="Submitted by {}".format(interaction.user.display_name), icon_url=interaction.user.display_avatar.url)
                embed.set_thumbnail(url=boss_dict[status[0]])

                await interaction.edit_original_message(content = '', embed = embed, view = None)
            
                print('updating sheet...')
                file_log(interaction.data['options'][0]['value'], interaction.data['options'][1]['value'], interaction.data['options'][2]['value'])
            else:
                await interaction.edit_original_message(content = '> Cancelled.', view = None)
                
        elif name == 'hello':
            await interaction.response.send_message(content = '> Hello! 👋')
            
        elif name == 'status':
            await interaction.response.defer()

            status = check_boss_status()
            boss_dict = {1:'https://static.wikia.nocookie.net/princess-connect/images/c/c1/Wyvern.png/revision/latest/scale-to-width-down/121?cb=20181125033728',2:'https://static.wikia.nocookie.net/princess-connect/images/8/8a/WildGriffon.png/revision/latest/scale-to-width-down/121?cb=20181125034631',3:'https://static.wikia.nocookie.net/princess-connect/images/f/f9/Megalapan.jpg/revision/latest/scale-to-width-down/500?cb=20181125035320',4:'https://static.wikia.nocookie.net/princess-connect/images/4/47/SpiritHorn.png/revision/latest/scale-to-width-down/126?cb=20181125035617',5:'https://static.wikia.nocookie.net/princess-connect/images/0/02/SagittariusBoss.jpg/revision/latest/scale-to-width-down/500?cb=20181125040010'}
            
            embed = nextcord.Embed(title="Current Boss Status", colour=nextcord.Colour.random(), description="__**Lap:**__ {}\n__**Boss:**__ {}\n__**Health:**__ {}".format(status[1], status[0], status[2]), timestamp=pytz.utc.localize(datetime.utcnow()).astimezone(pytz.timezone('US/Eastern')))
            embed.set_author(name="Misato Bot", url="https://discordapp.com", icon_url="https://cdn.discordapp.com/avatars/892079008857096253/f749c788d86c481e26096319eae36bc1.png?size=256")
            embed.set_footer(text="Requested by {}".format(interaction.user.display_name), icon_url=interaction.user.display_avatar.url)
            embed.set_thumbnail(url=boss_dict[status[0]])
            
            await interaction.edit_original_message(embed = embed)

        elif name == 'team':
            await interaction.response.defer()

            df = remaining_teams(str(interaction.data['options'][0]['value']),str(get_day()))
            wacbserver = client.get_guild(788287235237609482)
            out_df = pd.DataFrame(columns = ['IGN', 'Discord_Name', 'Status'])

            for member in wacbserver.members:
                for key, item in df.iterrows():
                    if item['Discord_ID'] == str(member.id):
                        ign = item['IGN']
                        if member.status == nextcord.Status.online:
                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'1💚'},ignore_index = True)
                        elif member.status == nextcord.Status.idle:
                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'2💛'},ignore_index = True)
                        elif member.status == nextcord.Status.dnd:
                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'3❤️'},ignore_index = True)
                        elif member.status == nextcord.Status.offline:
                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'4🤍'},ignore_index = True)

            out_df = out_df.sort_values(by = ['Status','IGN'])
            out_df['Status'] = out_df['Status'].apply(lambda x:x[1:])
            out_list = [f"{item['Status']} {item['IGN']} - {item['Discord_Name']}" for key,item in out_df.iterrows()]
            out_str = f"__{interaction.data['options'][0]['value']} Remaining__\n{len(out_list)}/30\n> " + '\n> '.join(out_list)

            await interaction.edit_original_message(content = out_str, allowed_mentions = nextcord.AllowedMentions(users = False))

        elif name == 'sl':
            if len(interaction.data['options']) == 1:
                await interaction.response.defer()

                membername = interaction.data['options'][0]['value']
                worksheet = get_worksheet('Summary')

                if interaction.data['options'][0]['name'] == 'mark':
                    if worksheet.cell(worksheet.find(membername).row, worksheet.find(f'Day {get_day()}').col).value == 'FALSE':
                        mark_unmark = 'Mark'
                    elif worksheet.cell(worksheet.find(membername).row, worksheet.find(f'Day {get_day()}').col).value == 'TRUE':
                        mark_unmark = 'Unmark'

                    view = confirmview()
                    await interaction.edit_original_message(content = f'> {mark_unmark} {membername}\'s S/L?', view = view)
                    await view.wait()

                    if view.value is None:
                        await interaction.edit_original_message(content = '> Timed out.', view = None)
                    elif view.value:
                        if mark_unmark == 'Mark':
                            await interaction.edit_original_message(content = f'> ✅ Marked an S/L for {membername}.', view = None)
                            worksheet.update_cell(worksheet.find(membername).row, worksheet.find(f'Day {get_day()}').col, True)
                        elif mark_unmark == 'Unmark':
                            await interaction.edit_original_message(content = f'> ❎ Unmarked an S/L for {membername}.', view = None)
                            worksheet.update_cell(worksheet.find(membername).row, worksheet.find(f'Day {get_day()}').col, False)
                    else:
                        await interaction.edit_original_message(content = '> Cancelled.', view = None)

                elif interaction.data['options'][0]['name'] == 'check':
                    if worksheet.cell(worksheet.find(membername).row, worksheet.find(f'Day {get_day()}').col).value == 'TRUE':
                        await interaction.edit_original_message(content = f'> ✅ {membername} has used their S/L today.')
                    else:
                        await interaction.edit_original_message(content = f'> ❎ {membername} has not used their S/L today.')
            else:
                await interaction.response.send_message(content = '> Please use only one argument.')
                
client.run(os.getenv('BOT_TOKEN'))