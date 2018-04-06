import json
import logging
import os
import signal
import sys

import discord
from discord.ext import commands
from cogs.utils import checks


def initLogging():
    logformat = "%(asctime)s %(name)s:%(levelname)s:%(message)s"
    logging.basicConfig(level=logging.INFO, format=logformat,
                        datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger("discord").setLevel(logging.WARNING)
    return logging.getLogger("porygon")


def sig_handler(signum, frame):
    logger.info("Exiting...")
    # logger.shutdown()
    sys.exit()



if __name__ == "__main__":
    logger = initLogging()
    logger.info("Initializing...")
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    try:
        with open("config.json") as c:
            config = json.load(c)
    except FileNotFoundError:
        logger.error("Config file not found, quitting!")
        sys.exit(-1)
    bot = commands.Bot(command_prefix=config['prefix'],
                       description='Porygon',
                       max_messages=100)
    bot.config = config


    @checks.check_permissions_or_owner(administrator=True)
    @bot.command(hidden=True)
    async def restart(ctx):
        await ctx.send("Restarting...")
        await bot.logout()
        os._exit(1)


    @checks.check_permissions_or_owner(administrator=True)
    @bot.command(hidden=True)
    async def shutdown(ctx):
        await ctx.send("Shutting down...")
        await bot.logout()
        os._exit(0)


    @bot.event
    async def on_command_error(ctx, error):
        error = getattr(error, 'original', error)
        if hasattr(ctx.command, 'on_error') or hasattr(ctx.cog, '_{0.__class__.__name__}__error'.format(ctx.cog)):
            return
        if isinstance(error, discord.ext.commands.CommandNotFound):
            return
        if isinstance(error, discord.ext.commands.CheckFailure):
            await ctx.send("{} You don't have permission to use this command.".format(ctx.message.author.mention))
        elif isinstance(error, discord.ext.commands.MissingRequiredArgument):
            await ctx.send("{} You are missing required arguments.".format(ctx.message.author.mention))
        else:
            if ctx.command:
                await ctx.send("An error occurred while processing the `{}` command.".format(ctx.command.name))
            logger.exception(error)


    @bot.event
    async def on_ready():
        logger.info("Connected.")
        main_server = discord.utils.get(bot.guilds, id=401014193211441153)

        bot.builds_channel = main_server.get_channel(401070313179185152)
        bot.commits_channel = main_server.get_channel(401017666577629214)
        bot.modlog_channel = main_server.get_channel(431429919185174547)
        bot.general_channel = main_server.get_channel(401014193211441161)

    for extension in os.listdir("cogs"):
        if extension.endswith('.py'):
            try:
                bot.load_extension("cogs." + extension[:-3])
            except Exception as e:
                logger.exception('Failed to load extension {}'.format(extension))

    bot.run(config['token'])
