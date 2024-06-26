#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 27 11:34:26 2021

@author: rmoctezuma
"""

import nextcord
from datetime import datetime, timezone
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

BOSS_ICONS = {1:'https://pricalc.b-cdn.net/jp/unit/extract/latest/icon_unit_305700.png',2:'https://pricalc.b-cdn.net/jp/unit/extract/latest/icon_unit_304600.png',3:'https://pricalc.b-cdn.net/jp/unit/extract/latest/icon_unit_301001.png',4:'https://pricalc.b-cdn.net/jp/unit/extract/latest/icon_unit_305800.png',5:'https://pricalc.b-cdn.net/jp/unit/extract/latest/icon_unit_302701.png'}
SHEET_NAMES = {'TamaParade': 'TamaParade Battle Logs', 'Eminence': 'Eminence Battle Logs', 'Salivation': 'Salivation Battle Logs', 'Infinity Kyaru': 'Infinity Kyaru Battle Logs'}

print(datetime.now())

def get_day():
    now = datetime.now(timezone.utc)
    if (now.day == 25 and now.hour >= 13) or (now.day == 26 and now.hour < 13):
        day = 1
    elif (now.day == 26 and now.hour >= 13) or (now.day == 27 and now.hour < 13):
        day = 2
    elif (now.day == 27 and now.hour >= 13) or (now.day == 28 and now.hour < 13):
        day = 3
    elif (now.day == 28 and now.hour >= 13) or (now.day == 29 and now.hour < 13):
        day = 4
    elif (now.day == 29 and now.hour >= 13) or (now.day == 30 and now.hour < 13):
        day = 5
    return(day)

def get_worksheet(spreadsheet_name, worksheet_name):
    gclient = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_KEYS))
    worksheet = gclient.open(spreadsheet_name).worksheet(worksheet_name)
    ws_df = gd.get_as_dataframe(worksheet, evaluate_formulas=True)
    return worksheet, ws_df

def file_log(clan_sheet, attacker, team, damage, pilot=''):
    worksheet, ws_df=get_worksheet(clan_sheet, 'Battle Log')
    ws_df.rename(columns={"Unnamed: 2": "Boss", "Unnamed: 5": "Attacker"}, inplace=True)
    target_row=0
    for index, row in ws_df.iterrows():
        if not(pd.isna(row['Boss'])) and pd.isna(row['Attacker']) and (index>1):
            target_row = index+2
            break
    if target_row > 0:
        worksheet.update('A' + str(target_row), get_day())
        worksheet.update('F' + str(target_row), attacker)
        worksheet.update('G' + str(target_row), team)
        worksheet.update('H' + str(target_row), damage)
        worksheet.update('I' + str(target_row), pilot)

def check_boss_status(clan_sheet):
    worksheet, ws_df = get_worksheet(clan_sheet, 'Battle Log')
    ws_df.columns = ws_df.iloc[0,:]
    boss=lap=health=0
    for index, row in ws_df.iterrows():
        # print(f"Checking row {index}, columns have [{row['Lap']}] and [{row['Boss']}] and [{row['Health']}]")
        if not(pd.isna(row['Lap'])) and not(pd.isna(row['Boss'])) and not(pd.isna(ws_df.iloc[index-1]['Health'])) and (index>0) and (row['Boss'] != '-'):
            boss=row['Boss']
            lap=row['Lap']
            health=ws_df.iloc[index-1]['Health']
    return (boss, lap, health)

def remaining_teams(clan_sheet, team, day):
    worksheet, df = get_worksheet(clan_sheet, 'Summary')
    
    print(type(worksheet.find(f'Day {day}').col))
    df = df.iloc[2:32, [0, 1, worksheet.find(f'Day {day}').col + int(team), worksheet.find(f'Day {day}').col + 5]]
    df.columns = ['IGN', 'Discord_ID', 'Remaining','Carryover']
    df['Discord_ID'] = df['Discord_ID'].apply(lambda x: x[2:-1])

    a_df = df[(df['Remaining'] != 0) & (df['Carryover'].isna())].drop(columns = ['Remaining', 'Carryover'])

    c_df = df[(df['Carryover'].fillna('xx').str[:2] == f'T{team}')].drop(columns = ['Remaining'])

    b_df = df[(df['Remaining'] != 0) & (df['Carryover']).notna()].drop(columns = ['Remaining'])

    return a_df, c_df, b_df

def individual_remaining_teams(clan_sheet, member, day):
    worksheet, df = get_worksheet(clan_sheet, 'Summary')
    day_column = worksheet.find(f'Day {day}').col

    df = df.iloc[2:32, [0, 1, day_column + 1, day_column + 2, day_column + 3, day_column + 4, day_column + 5]]
    df.columns = ['IGN', 'Discord_ID', 'T1', 'T2', 'T3', 'T4', 'Carryover']
    df['Discord_ID'] = df['Discord_ID'].apply(lambda x: x[2:-1])

    df = df[(df['IGN'] == member)]

    return df

def overflow(clan_sheet, day):
    worksheet, df = get_worksheet(clan_sheet, 'Summary')

    df = df.iloc[2:32, [0, 1, worksheet.find(f'Day {day}').col + 5]]
    df.columns = ['IGN', 'Discord_ID', 'Carryover']
    df['Discord_ID'] = df['Discord_ID'].apply(lambda x: x[2:-1])

    c_df = df[df['Carryover'].notna()]

    return c_df

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
        clan = ''

        if interaction.channel.category_id == 923112036265754715:
            clan_sheet = SHEET_NAMES['TamaParade']
            clan = 'TamaParade'
        elif interaction.channel.category_id == 923026389807013910:
            clan_sheet = SHEET_NAMES['Eminence']
            clan = 'Eminence'
        elif interaction.channel.category_id == 925548128239755266:
            clan_sheet = SHEET_NAMES['Salivation']
            clan = 'Salivation'
        elif interaction.channel.category_id == 946627063534747678:
            clan_sheet = SHEET_NAMES['Infinity Kyaru']
            clan = 'Infinity Kyaru'
        else:
            await interaction.response.send_message(content = '> Please use commands in your clan\'s discord channels.')

        if name == 'log':
            await interaction.response.defer()

            status = check_boss_status(clan_sheet)
            if len(interaction.data['options']) == 4:
                text = '> Log an attack from {} using {} on Lap {} Boss {} with {} damage piloted by {}?'.format(interaction.data['options'][0]['value'], interaction.data['options'][1]['value'], status[1], status[0], interaction.data['options'][2]['value'], interaction.data['options'][3]['value'])
                desc = "__**Attacker:**__ {}\n__**Team:**__ {}\n__**Lap:**__ {}\n__**Boss:**__ {}\n__**Damage:**__ {}\n__**Pilot:**__ {}".format(interaction.data['options'][0]['value'], interaction.data['options'][1]['value'], status[1], status[0], interaction.data['options'][2]['value'], interaction.data['options'][3]['value'])
            else:
                text = '> Log an attack from {} using {} on Lap {} Boss {} with {} damage?'.format(interaction.data['options'][0]['value'], interaction.data['options'][1]['value'], status[1], status[0], interaction.data['options'][2]['value'])
                desc = "__**Attacker:**__ {}\n__**Team:**__ {}\n__**Lap:**__ {}\n__**Boss:**__ {}\n__**Damage:**__ {}".format(interaction.data['options'][0]['value'], interaction.data['options'][1]['value'], status[1], status[0], interaction.data['options'][2]['value'])
            view = confirmview()

            await interaction.edit_original_message(content = text, view = view)
            await view.wait()
            if view.value is None:
                await interaction.edit_original_message(content = '> Timed out.', view = None)
            elif view.value:
                embed = nextcord.Embed(title="Priconne Damage Logging", colour=nextcord.Colour.random(), description=desc, timestamp=pytz.utc.localize(datetime.utcnow()).astimezone(pytz.timezone('US/Eastern')))
                embed.set_author(name=client.user.name + ' Bot', icon_url=client.user.display_avatar.url)
                embed.set_footer(text="Submitted by {}".format(interaction.user.display_name), icon_url=interaction.user.display_avatar.url)
                embed.set_thumbnail(url=BOSS_ICONS[status[0]])

                await interaction.edit_original_message(content = '', embed = embed, view = None)
            
                print('updating sheet...')
                if len(interaction.data['options']) == 4:
                    file_log(clan_sheet, interaction.data['options'][0]['value'], interaction.data['options'][1]['value'], interaction.data['options'][2]['value'], interaction.data['options'][3]['value'])
                else:
                    file_log(clan_sheet, interaction.data['options'][0]['value'], interaction.data['options'][1]['value'], interaction.data['options'][2]['value'])

            else:
                await interaction.edit_original_message(content = '> Cancelled.', view = None)
                
        elif name == 'hello':
            await interaction.response.send_message(content = '> Hello! 👋')
            
        elif name == 'status':
            await interaction.response.defer()

            status = check_boss_status(clan_sheet)

            embed = nextcord.Embed(title="Current Boss Status", colour=nextcord.Colour.random(), description="__**Lap:**__ {}\n__**Boss:**__ {}\n__**Health:**__ {}".format(status[1], status[0], status[2]), timestamp=pytz.utc.localize(datetime.utcnow()).astimezone(pytz.timezone('US/Eastern')))
            embed.set_author(name=client.user.name + ' Bot', icon_url=client.user.display_avatar.url)
            embed.set_footer(text="Requested by {}".format(interaction.user.display_name), icon_url=interaction.user.display_avatar.url)
            embed.set_thumbnail(url=BOSS_ICONS[status[0]])
            
            await interaction.edit_original_message(embed = embed)

        elif name == 'team':
            if len(interaction.data['options']) == 1:
                await interaction.response.defer()

                if interaction.data['options'][0]['name'] == 'all':

                    a_df, c_df, b_df = remaining_teams(clan_sheet, str(interaction.data['options'][0]['value']),str(get_day()))
                    df_list = [a_df, c_df, b_df]

                    if clan == 'Infinity Kyaru':
                        clanserver = client.get_guild(654218111003787264)
                    elif clan == 'TamaParade' or clan == 'Eminence' or clan == 'Salivation':
                        clanserver = client.get_guild(923026389807013908)

                    a_out = pd.DataFrame(columns = ['IGN', 'Discord_Name', 'Status'])
                    c_out = pd.DataFrame(columns = ['IGN', 'Discord_Name', 'Status', 'Carryover'])
                    b_out = pd.DataFrame(columns = ['IGN', 'Discord_Name', 'Status', 'Carryover'])
                    out_list = [a_out, c_out, b_out]

                    for member in clanserver.members:
                        for index, df in enumerate(df_list):
                            out_df = out_list[index]
                            for key, item in df.iterrows():
                                if item['Discord_ID'] == str(member.id):
                                    ign = item['IGN']
                                    if index == 1 or index == 2:
                                        carryover = item['Carryover']
                                        if member.status == nextcord.Status.online:
                                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'1💚','Carryover':carryover},ignore_index = True)
                                        elif member.status == nextcord.Status.idle:
                                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'2💛','Carryover':carryover},ignore_index = True)
                                        elif member.status == nextcord.Status.dnd:
                                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'3❤️','Carryover':carryover},ignore_index = True)
                                        elif member.status == nextcord.Status.offline:
                                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'4🤍','Carryover':carryover},ignore_index = True)
                                    else:
                                        if member.status == nextcord.Status.online:
                                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'1💚'},ignore_index = True)
                                        elif member.status == nextcord.Status.idle:
                                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'2💛'},ignore_index = True)
                                        elif member.status == nextcord.Status.dnd:
                                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'3❤️'},ignore_index = True)
                                        elif member.status == nextcord.Status.offline:
                                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'4🤍'},ignore_index = True)
                            out_list[index] = out_df
                    
                    for index, out_df in enumerate(out_list):
                        out_df = out_df.sort_values(by = ['Status','IGN'])
                        out_df['Status'] = out_df['Status'].apply(lambda x:x[1:])
                        if index == 1 or index == 2:
                            out_list[index] = [f"{item['Status']} {item['IGN']} - {item['Discord_Name']} {item['Carryover']}" for key,item in out_df.iterrows()]
                        else:
                            out_list[index] = [f"{item['Status']} {item['IGN']} - {item['Discord_Name']}" for key,item in out_df.iterrows()]

                    out_str = ''
                    if not(a_df.empty):
                        out_str += f"__**T{interaction.data['options'][0]['value']} Available:**__ {len(out_list[0])}\n> " + '\n> '.join(out_list[0]) + '\n\n'
                    if not(c_df.empty):
                        out_str += f"__**T{interaction.data['options'][0]['value']} Carryover:**__ {len(out_list[1])}\n> " + '\n> '.join(out_list[1]) + '\n\n'
                    if not(b_df.empty):
                        out_str += f"__**T{interaction.data['options'][0]['value']} Blocked:**__ {len(out_list[2])}\n> " + '\n> '.join(out_list[2]) + '\n\n'
                    if out_str == '':
                        out_str += f"__**No T{interaction.data['options'][0]['value']} remaining.**__"

                    await interaction.edit_original_message(content = out_str, allowed_mentions = nextcord.AllowedMentions(users = False))

                elif interaction.data['options'][0]['name'] == 'specific':
                    df = individual_remaining_teams(clan_sheet, interaction.data['options'][0]['value'], str(get_day()))

                    if clan == 'Infinity Kyaru':
                        clanserver = client.get_guild(654218111003787264)
                    elif clan == 'TamaParade' or clan == 'Eminence' or clan == 'Salivation':
                        clanserver = client.get_guild(923026389807013908)

                    for member in clanserver.members:
                        if df.iloc[0]['Discord_ID'] == str(member.id):

                            teams_list = ['❌', '❌', '❌', '❌', 'N/A']
                            if df.iloc[0]['T1'] == 1:
                                teams_list[0] = '✅'
                            if df.iloc[0]['T2'] == 1:
                                teams_list[1] = '✅'
                            if df.iloc[0]['T3'] == 1:
                                teams_list[2] = '✅'
                            if df.iloc[0]['T4'] == 1:
                                teams_list[3] = '✅'
                            if pd.notna(df.iloc[0]['Carryover']):
                                teams_list[4] = str(df.iloc[0]['Carryover'])

                            embed = nextcord.Embed(title=f"__{df.iloc[0]['IGN']}'s teams__", colour=nextcord.Colour.random(), description=f"**T1:** {teams_list[0]}\n**T2:** {teams_list[1]}\n**T3**: {teams_list[2]}\n**T4**: {teams_list[3]}\n**Carryover:** {teams_list[4]}", timestamp=pytz.utc.localize(datetime.utcnow()).astimezone(pytz.timezone('US/Eastern')))
                            embed.set_author(name=client.user.name + ' Bot', icon_url=client.user.display_avatar.url)
                            embed.set_footer(text="Requested by {}".format(interaction.user.display_name), icon_url=interaction.user.display_avatar.url)
                            embed.set_thumbnail(url=member.display_avatar.url)

                            await interaction.edit_original_message(embed = embed)

            else:
                await interaction.response.send_message(content = '> Please use only one argument.')
        
        elif name == 'overflow':
            await interaction.response.defer()

            c_df = overflow(clan_sheet, str(get_day()))

            if clan == 'Infinity Kyaru':
                clanserver = client.get_guild(654218111003787264)
            elif clan == 'TamaParade' or clan == 'Eminence' or clan == 'Salivation':
                clanserver = client.get_guild(923026389807013908)

            out_df = pd.DataFrame(columns = ['IGN', 'Discord_Name', 'Status', 'Carryover'])

            for member in clanserver.members:
                for key, item in c_df.iterrows():
                    if item['Discord_ID'] == str(member.id):
                        ign = item['IGN']
                        carryover = item['Carryover']
                        if member.status == nextcord.Status.online:
                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'1💚','Carryover':carryover},ignore_index = True)
                        elif member.status == nextcord.Status.idle:
                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'2💛','Carryover':carryover},ignore_index = True)
                        elif member.status == nextcord.Status.dnd:
                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'3❤️','Carryover':carryover},ignore_index = True)
                        elif member.status == nextcord.Status.offline:
                            out_df = out_df.append({'IGN':ign,'Discord_Name':member.mention,'Status':'4🤍','Carryover':carryover},ignore_index = True)

            out_df = out_df.sort_values(by = ['Status','IGN'])
            out_df['Status'] = out_df['Status'].apply(lambda x:x[1:])
            out_df = [f"{item['Status']} {item['IGN']} - {item['Discord_Name']} {item['Carryover']}" for key,item in out_df.iterrows()]
            
            if not(c_df.empty):
                out_str = f"__**Overflows:**__ {len(out_df)}\n> " + '\n> '.join(out_df) + '\n\n'
            else:
                out_str = f"__**No current overflows.**__"

            await interaction.edit_original_message(content = out_str, allowed_mentions = nextcord.AllowedMentions(users = False))

        elif name == 'sl':
            if len(interaction.data['options']) == 1:
                await interaction.response.defer()

                membername = interaction.data['options'][0]['value']
                worksheet, ws_df = get_worksheet(clan_sheet, 'Summary')

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