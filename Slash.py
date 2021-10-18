# Author: Michael Conard
# Purpose: An Axie Infinity utility bot. Gives QR codes and daily progress/alerts.

import discord
import os
import traceback
import math
import configparser
import json

from discord.ext import tasks, commands
from dislash import slash_commands
from dislash.interactions import *
from datetime import datetime, timezone

from SecretStorage import *
from Common import *
from UtilBot import *
from Commands import *


# Slash Commands

@slash.command(
    name="help",
    description="Returns information on the available commands",
    guild_ids=serverIds
)
async def helpsSlash(ctx):
    await ctx.create_response(type=5)
    
    discordId = ctx.author.id
    await helpCommand(ctx, discordId, True)


@slash.command(
    name="export",
    description="Returns an export of all scholars",
    guild_ids=serverIds
)
async def export(ctx):
    await ctx.create_response(type=5)
    
    discordId = ctx.author.id
    isManager = False
    if discordId in managerIds:
        isManager = True
    await exportCommand(ctx, isManager, True)


@slash.command(
    name="qr",
    description="Generate and recieve a QR code for mobile login",
    guild_ids=serverIds
)
async def qr(ctx):
    await ctx.create_response(type=5)
    
    discordId = ctx.author.id
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id

    isManager = False
    if discordId in managerIds:
        isManager = True

    await qrCommand(ctx, isManager, discordId, guildId, True)


@slash.command(
    name="battles",
    description="Generate a summary of a player's recent battle information",
    guild_ids=serverIds,
    options=[
        Option(
            name="name",
            description="The scholar name or ronin address to lookup",
            required=False,
            type=Type.STRING
        )
    ]
)
async def battles(ctx):
    await ctx.create_response(type=5)
    
    discordId = ctx.author.id
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id

    isManager = False
    if discordId in managerIds:
        isManager = True

    args = ["battles"]
    if ctx.data.get_option('name') is not None:
        args.append(ctx.data.get_option('name').value)

    await battlesCommand(ctx, args, isManager, discordId, guildId, True)


@slash.command(
    name="daily",
    description="Generate a summary of a player's daily activity",
    guild_ids=serverIds,
    options=[
        Option(
            name="name",
            description="The username to lookup",
            required=False,
            type=Type.STRING
        )
    ]
)
async def daily(ctx):
    await ctx.create_response(type=5)
    
    discordId = ctx.author.id
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id

    isManager = False
    if discordId in managerIds:
        isManager = True

    args = ["daily"]
    if ctx.data.get_option('name') is not None:
        args.append(ctx.data.get_option('name').value)

    await dailyCommand(ctx, args, isManager, discordId, guildId, True)


@slash.command(
    name="alert",
    description="Triggers a manual alert to your alert channel",
    guild_ids=serverIds,
    options=[
        Option(
            name="ping",
            description="Whether or not to ping users with alerts",
            required=True,
            type=Type.BOOLEAN
        )
    ]
)
async def alert(ctx):
    global forceAlert
    global alertPing

    await ctx.create_response(type=5)
    
    discordId = ctx.author.id
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id

    isManager = False
    if discordId in managerIds:
        isManager = True

    if not isManager:
        await ctx.reply('Hello <@' + str(discordId) + '>! Unfortunately, you must be a manager to use this command.')
        return

    args = ["alert"]
    if ctx.data.get_option('ping') is not None:
        toPing = bool(ctx.data.get_option('ping').value)
        if toPing:
            args.append("1")

    await alertsCommand(ctx, args, True)


@slash.command(
    name="axies",
    description="Gets a player's Axie team",
    guild_ids=serverIds,
    options=[
        Option(
            name="name",
            description="The username to lookup",
            required=False,
            type=Type.STRING
        ),
        Option(
            name="index",
            description="The team index, from 0 to 20",
            required=False,
            type=Type.INTEGER
        ),
        Option(
            name="mobile",
            description="Whether to display a mobile view or desktop view",
            required=False,
            type=Type.BOOLEAN
        )
    ]
)
async def axies(ctx):
    await ctx.create_response(type=5)
    
    discordId = ctx.author.id
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id

    isManager = False
    if discordId in managerIds:
        isManager = True

    args = ["axies"]
    if ctx.data.get_option('name') is not None:
        args.append(str(ctx.data.get_option('name').value))
    else:
        args.append("")
    if ctx.data.get_option('index') is not None:
        args.append(int(ctx.data.get_option('index').value))
    else:
        args.append("")
    if ctx.data.get_option('mobile') is not None:
        mobile = bool(ctx.data.get_option('mobile').value)
        if mobile:
            args.append("1")
        else:
            args.append("0")
    else:
        args.append("0")

    await axiesCommand(ctx, args, isManager, discordId, guildId, True)


@slash.command(
    name="summary",
    description="Generate a summary view of the scholars",
    guild_ids=serverIds,
    options=[
        Option(
            name="sort",
            description="The category to sort on",
            required=False,
            choices=[
                OptionChoice(
                    name="claim",
                    value="claim"
                ),
                OptionChoice(
                    name="slp",
                    value="slp"
                ),
                OptionChoice(
                    name="adventure",
                    value="adventure"
                ),
                OptionChoice(
                    name="mmr",
                    value="mmr"
                ),
                OptionChoice(
                    name="arena",
                    value="arena"
                )
            ],
            type=Type.STRING
        ),
        Option(
            name="ascending",
            description="Whether to sort ascending or descending",
            required=False,
            type=Type.BOOLEAN
        ),
    ]
)
async def summary(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id

    isManager = False
    if discordId in managerIds:
        isManager = True

    # argument processing    
    args = ["summary"]
    if ctx.data.get_option('sort') is not None:
        args.append(str(ctx.data.get_option('sort').value))
    else:
        args.append("slp")

    if ctx.data.get_option('ascending') is not None:
        asc = bool(ctx.data.get_option('ascending').value)
        if asc:
            args.append("asc")
        else:
            args.append("desc")
    else:
        args.append("desc")

    await summaryCommand(ctx, args, isManager, discordId, guildId, True)


@slash.command(
    name="top",
    description="Generate a top 10 view of the scholars",
    guild_ids=serverIds,
    options=[
        Option(
            name="category",
            description="The category to rank on",
            required=False,
            choices=[
                OptionChoice(
                    name="slp",
                    value="slp"
                ),
                OptionChoice(
                    name="adventure",
                    value="adventure"
                ),
                OptionChoice(
                    name="arena",
                    value="arena"
                )
            ],
            type=Type.STRING
        )
    ]
)
async def top(ctx):
    await ctx.create_response(type=5)
    
    discordId = ctx.author.id
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id

    isManager = False
    if discordId in managerIds:
        isManager = True

    # argument processing    
    args = ["summary"]
    if ctx.data.get_option('category') is not None:
        args.append(str(ctx.data.get_option('category').value))
    else:
        args.append("arena")

    await topCommand(ctx, args, isManager, discordId, guildId, True)

