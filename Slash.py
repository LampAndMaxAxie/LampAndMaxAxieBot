# Author: Michael Conard
# Purpose: An Axie Infinity utility bot. Gives QR codes and daily progress/alerts.

import discord
import os
import traceback
import json

from discord.ext import commands
from dislash import slash_commands
from dislash.interactions import *
from datetime import datetime, timezone

from Commands import *
from Common import slash, client, serverIds
import DB

# Slash Commands

@slash.command(
    name="help",
    description="Returns information on the available commands",
    guild_ids=serverIds
)
async def helpSlash(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
        isManager = True
    await helpCommand(ctx, isManager, discordId, True)


@slash.command(
    name="payout",
    description="Process a payout for yourself (or discord ID if you're a manager)",
    guild_ids=serverIds,
    options=[
        Option(
            name="discordid",
            description="The user to payout (only if you're a manager)",
            required=False,
            type=Type.STRING
        )
    ]
)
async def payoutSlash(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
        isManager = True
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id
    
    args = ["payout"]
    if ctx.data.get_option('discordid') is not None:
        args.append(ctx.data.get_option('discordid').value)

    await payoutCommand(ctx, args, isManager, discordId, guildId, True)


@slash.command(
    name="mass_payout",
    description="Trigger a mass payout of all or a range of scholar accounts",
    guild_ids=serverIds,
    options=[
        Option(
            name="seednum",
            description="The seed index to payout (NOT YOUR ACTUAL SEED PHRASE)",
            required=False,
            type=Type.INTEGER
        ),
        Option(
            name="minaccount",
            description="The minimum account index on the specified seed",
            required=False,
            type=Type.INTEGER
        ),
        Option(
            name="maxaccount",
            description="The maximum account index on the specified seed",
            required=False,
            type=Type.INTEGER
        ),
    ]
)
async def massPayoutSlash(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
        isManager = True
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id
    
    args = ["massPayout"]
    if ctx.data.get_option('seednum') is not None:
        args.append(ctx.data.get_option('seednum').value)
    if ctx.data.get_option('minaccount') is not None:
        args.append(ctx.data.get_option('minaccount').value)
    if ctx.data.get_option('maxaccount') is not None:
        args.append(ctx.data.get_option('maxaccount').value)

    await payoutAllScholars(ctx, args, isManager, discordId, guildId, True)


@slash.command(
    name="set_property",
    description="Sets a property like massPay",
    guild_ids=serverIds,
    options=[
        Option(
            name="property",
            description="The property to change",
            required=True,
            type=Type.STRING
        ),
        Option(
            name="value",
            description="The value to set",
            required=True,
            type=Type.STRING
        )
    ]
)
async def setProp(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
        isManager = True
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id
    
    args = ["setProperty"]
    if ctx.data.get_option('property') is not None:
        args.append(ctx.data.get_option('property').value)
    if ctx.data.get_option('value') is not None:
        args.append(ctx.data.get_option('value').value)

    await setPropertyCommand(ctx, args, isManager, discordId, guildId, True)

@slash.command(
    name="get_property",
    description="Gets a property like massPay",
    guild_ids=serverIds,
    options=[
        Option(
            name="property",
            description="The property to change",
            required=True,
            type=Type.STRING
        )
    ]
)
async def getProp(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
        isManager = True
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id
    
    args = ["getProperty"]
    if ctx.data.get_option('property') is not None:
        args.append(ctx.data.get_option('property').value)

    await getPropertyCommand(ctx, args, isManager, discordId, guildId, True)


@slash.command(
    name="add_scholar",
    description="Adds a scholar to the database",
    guild_ids=serverIds,
    options=[
        Option(
            name="seednum",
            description="Which seed the scholar account is on",
            required=True,
            type=Type.INTEGER
        ),
        Option(
            name="accountnum",
            description="Which account on the seed",
            required=True,
            type=Type.INTEGER
        ),
        Option(
            name="accountaddr",
            description="Ronin address for the account",
            required=True,
            type=Type.STRING
        ),
        Option(
            name="discordid",
            description="Discord ID for the scholar (not name, that can be changed)",
            required=True,
            type=Type.STRING
        ),
        Option(
            name="scholarshare",
            description="Scholar payout share between 0.50 and 1.00",
            required=True,
            type=Type.STRING
        ),
        Option(
            name="payoutaddr",
            description="Scholar's payout address (optional, they can add it later)",
            required=False,
            type=Type.STRING
        )
    ]
)
async def addScholarSlash(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
        isManager = True
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id
    
    args = ["addScholar"]
    if ctx.data.get_option('seednum') is not None:
        args.append(str(ctx.data.get_option('seednum').value))
    if ctx.data.get_option('accountnum') is not None:
        args.append(str(ctx.data.get_option('accountnum').value))
    if ctx.data.get_option('accountaddr') is not None:
        args.append(ctx.data.get_option('accountaddr').value)
    if ctx.data.get_option('discordid') is not None:
        args.append(ctx.data.get_option('discordid').value)
    if ctx.data.get_option('scholarshare') is not None:
        args.append(ctx.data.get_option('scholarshare').value)
    if ctx.data.get_option('payoutaddr') is not None:
        if ctx.data.get_option('payoutaddr').value != "":
            args.append(ctx.data.get_option('payoutaddr').value)

    logger.info(args)
    await addScholar(ctx, args, isManager, discordId, guildId, True)


@slash.command(
    name="remove_scholar",
    description="Removes a user's scholar status from the database",
    guild_ids=serverIds,
    options=[
        Option(
            name="discordid",
            description="Discord ID for the scholar (not name, that can be changed)",
            required=True,
            type=Type.STRING
        )
    ]
)
async def removeScholarSlash(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
        isManager = True
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id
    
    args = ["removeScholar"]
    if ctx.data.get_option('discordid') is not None:
        args.append(ctx.data.get_option('discordid').value)

    await removeScholar(ctx, args, isManager, discordId, guildId, True)

@slash.command(
    name="update_scholar_share",
    description="Promotes/demotes a scholars payout share",
    guild_ids=serverIds,
    options=[
        Option(
            name="discordid",
            description="Discord ID for the scholar (not name, that can be changed)",
            required=True,
            type=Type.STRING
        ),
        Option(
            name="scholarshare",
            description="Scholar payout share from 0.50 to 1.00",
            required=True,
            type=Type.STRING
        )
    ]
)
async def updateShareSlash(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
        isManager = True
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id
    
    args = ["updateScholarShare"]
    if ctx.data.get_option('discordid') is not None:
        args.append(ctx.data.get_option('discordid').value)
    if ctx.data.get_option('scholarshare') is not None:
        args.append(ctx.data.get_option('scholarshare').value)

    await updateScholarShare(ctx, args, isManager, discordId, guildId, True)


@slash.command(
    name="update_scholar_login",
    description="Stores the scholar's email/pass long",
    guild_ids=serverIds,
    options=[
        Option(
            name="discordid",
            description="Discord ID for the scholar (not name, that can be changed)",
            required=True,
            type=Type.STRING
        ),
        Option(
            name="accountaddr",
            description="The account's ronin address",
            required=True,
            type=Type.STRING
        ),
        Option(
            name="accountemail",
            description="The account's email",
            required=True,
            type=Type.STRING
        ),
        Option(
            name="accountpass",
            description="The account's password",
            required=True,
            type=Type.STRING
        )
    ]
)
async def updateLoginSlash(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
        isManager = True
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id
    
    args = ["updateScholarLogin"]
    if ctx.data.get_option('discordid') is not None:
        args.append(ctx.data.get_option('discordid').value)
    if ctx.data.get_option('accountaddr') is not None:
        args.append(ctx.data.get_option('accountaddr').value)
    if ctx.data.get_option('accountemail') is not None:
        args.append(ctx.data.get_option('accountemail').value)
    if ctx.data.get_option('accountpass') is not None:
        args.append(ctx.data.get_option('accountpass').value)

    await updateScholarLogin(ctx, args, isManager, discordId, guildId, True)


@slash.command(
    name="update_scholar_payout",
    description="Updates the scholar's payout address",
    guild_ids=serverIds,
    options=[
        Option(
            name="payoutaddr",
            description="The new payout address",
            required=True,
            type=Type.STRING
        ),
        Option(
            name="discordid",
            description="Discord ID for the scholar (not name, that can be changed)",
            required=False,
            type=Type.STRING
        )
    ]
)
async def updatePayoutSlash(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
        isManager = True
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id
    
    args = ["updateScholarAddress"]
    if ctx.data.get_option('payoutaddr') is not None:
        args.append(ctx.data.get_option('payoutaddr').value)
    if ctx.data.get_option('discordid') is not None:
        args.append(ctx.data.get_option('discordid').value)

    await updateScholarAddress(ctx, args, isManager, discordId, guildId, True)


@slash.command(
    name="add_manager",
    description="Gives a user manager powers",
    guild_ids=serverIds,
    options=[
        Option(
            name="discordid",
            description="The user to make a manager",
            required=True,
            type=Type.STRING
        )
    ]
)
async def addManagerSlash(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
        isManager = True
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id
    
    args = ["addManager"]
    if ctx.data.get_option('discordid') is not None:
        args.append(ctx.data.get_option('discordid').value)

    await addManager(ctx, args, isManager, discordId, guildId, True)


@slash.command(
    name="remove_manager",
    description="Removes a user's manager powers",
    guild_ids=serverIds,
    options=[
        Option(
            name="discordid",
            description="The user to remove as a manager",
            required=True,
            type=Type.STRING
        )
    ]
)
async def removeManagerSlash(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
        isManager = True
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id
    
    args = ["removeManager"]
    if ctx.data.get_option('discordid') is not None:
        args.append(ctx.data.get_option('discordid').value)

    await removeManager(ctx, args, isManager, discordId, guildId, True)

@slash.command(
    name="export",
    description="Returns an export of all scholars",
    guild_ids=serverIds
)
async def export(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    isManager = False
    if await DB.isManager(discordId):
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
    if await DB.isManager(discordId):
        isManager = True

    await qrCommand(ctx, isManager, discordId, guildId, True)


@slash.command(
    name="login",
    description="Fetch account login info (email/pass)",
    guild_ids=serverIds
)
async def login(ctx):
    await ctx.create_response(type=5)

    discordId = ctx.author.id
    guild = ctx.guild
    guildId = None
    if guild is not None:
        guildId = guild.id

    isManager = False
    if await DB.isManager(discordId):
        isManager = True

    await loginInfoCommand(ctx, isManager, discordId, guildId, True)

"""
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
    if await DB.isManager(discordId):
        isManager = True

    args = ["battles"]
    if ctx.data.get_option('name') is not None:
        args.append(ctx.data.get_option('name').value)

    await battlesCommand(ctx, args, isManager, discordId, guildId, True)
"""

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
    if await DB.isManager(discordId):
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
    if await DB.isManager(discordId):
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
    if await DB.isManager(discordId):
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
    if await DB.isManager(discordId):
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
    if await DB.isManager(discordId):
        isManager = True

    # argument processing    
    args = ["summary"]
    if ctx.data.get_option('category') is not None:
        args.append(str(ctx.data.get_option('category').value))
    else:
        args.append("arena")

    await topCommand(ctx, args, isManager, discordId, guildId, True)

