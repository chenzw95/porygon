import logging
import discord
import pkg_resources
import contextlib
import sys
import inspect
import os
import shutil
import glob
import math
import textwrap
from discord.ext import commands
from io import StringIO
from traceback import format_exc
from cogs.utils.checks import *
from contextlib import redirect_stdout

from discord.ext import commands
from .utils import checks

# Common imports that can be used by the debugger.
import os
import requests
import json
import gc
import datetime
import time
import traceback
import prettytable
import re
import io
import asyncio
import discord
import random
import subprocess
from bs4 import BeautifulSoup
import urllib
import psutil


class Debug:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("porygon.{}".format(__name__))
        self._last_result = None

    @commands.command()
    @checks.check_permissions_or_owner(administrator=True)
    async def rehash(self, ctx):
        """Reloads bot configuration."""
        self.logger.info("Reloading configuration...")
        try:
            with open("config.json") as c:
                config = json.load(c)
            for channel, cid in config['channels'].items():
                setattr(self.bot, "{}_channel".format(channel), self.bot.main_server.get_channel(cid))
            for role, roleid in config['roles'].items():
                setattr(self.bot, "{}_role".format(role), discord.utils.get(self.bot.main_server.roles, id=roleid))
        except Exception as e:
            await ctx.send("⚠ Operation failed!\n```\n{}: {}```".format(type(e).__name__, e))
            self.logger.exception(e)
        await ctx.send("✅ Configuration reloaded.")

    @commands.command()
    @checks.check_permissions_or_owner(administrator=True)
    async def reload(self, ctx, module: str):
        if module[0:5] != "cogs.":
            module = "cogs." + module
        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
            await ctx.send("✅ Extension reloaded.")
        except Exception as e:
            await ctx.send("⚠ Operation failed!\n```\n{}: {}```".format(type(e).__name__, e))
            self.logger.exception(e)

    @commands.command()
    @checks.check_permissions_or_owner(administrator=True)
    async def load(self, ctx, module: str):
        if module[0:5] != "cogs.":
            module = "cogs." + module
        try:
            self.bot.load_extension(module)
            await ctx.send("✅ Extension loaded.")
        except Exception as e:
            await ctx.send("⚠ Operation failed!\n```\n{}: {}```".format(type(e).__name__, e))
            self.logger.exception(e)

    @commands.command()
    @checks.check_permissions_or_owner(administrator=True)
    async def unload(self, ctx, module: str):
        if module[0:5] != "cogs.":
            module = "cogs." + module
        if module == "cogs.debug":
            return await ctx.send("⛔ You may not unload this!")
        try:
            self.bot.unload_extension(module)
            await ctx.send("✅ Extension unloaded.")
        except Exception as e:
            await ctx.send("⚠ Operation failed!\n```\n{}: {}```".format(type(e).__name__, e))
            self.logger.exception(e)

    @commands.command(aliases=['ri'])
    @commands.guild_only()
    async def roleinfo(self, ctx, *, role: discord.Role):
        embed = discord.Embed(title="Role information", color=role.color, timestamp=ctx.message.created_at)
        embed.add_field(name="Name", value=role.name).add_field(name="ID", value=role.id)
        embed.add_field(name="Hoisted", value=role.hoist, inline=False).add_field(name="Mentionable", value=role.mentionable)
        await ctx.send(embed=embed)

    @commands.command(aliases=['ui'])
    @commands.guild_only()
    async def userinfo(self, ctx, *, raw_member=None):
        if not raw_member:
            member = ctx.author
        else:
            try:
                member = await commands.MemberConverter().convert(ctx, raw_member)
            except commands.BadArgument:
                return await ctx.send("❌ User not found. Search terms are case sensitive.")
        embed = discord.Embed(title="{} ({})".format(member, member.display_name), color=member.top_role.color, timestamp=ctx.message.created_at)
        embed.set_author(name="User information")
        embed.add_field(name="ID", value=member.id).add_field(name="Status", value=member.status)
        embed.add_field(name="Activity", value=member.activity)
        if len(member.roles) > 1:
            embed.add_field(name="Roles", value=", ".join([str(role) for role in member.roles[1:]]), inline=False)
        else:
            embed.add_field(name="Roles", value="None", inline=False)
        embed.add_field(name="Created at", value=member.created_at.__format__('%A, %d. %B %Y @ %H:%M:%S'))
        embed.add_field(name="Joined at", value=member.joined_at.__format__('%A, %d. %B %Y @ %H:%M:%S'))
        await ctx.send(embed=embed)

    @roleinfo.error
    @userinfo.error
    async def info_handler(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, discord.ext.commands.BadArgument):
            await ctx.send("❌ Object not found. Search terms are case sensitive.")
        elif isinstance(error, discord.ext.commands.NoPrivateMessage):
            await ctx.send("⚠ This command must be executed in a server!")
        else:
            if ctx.command:
                await ctx.send("An error occurred while processing the `{}` command.".format(ctx.command.name))
            self.logger.exception(error, exc_info=error)

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    # Executes/evaluates code.Pretty much the same as Rapptz implementation for RoboDanny with slight variations.
    async def interpreter(self, env, code, ctx):
        body = self.cleanup_code(code)
        stdout = io.StringIO()

        os.chdir(os.getcwd())
        with open('%s/cogs/utils/temp.txt' % os.getcwd(), 'w') as temp:
            temp.write(body)

        to_compile = 'async def func():\n{}'.format(textwrap.indent(body, "  "))

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send('```\n{}: {}\n```'.format(e.__class__.__name__, e))

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.message.add_reaction("❌")
            await ctx.send('```\n{}{}\n```'.format(value, traceback.format_exc()))
        else:
            await ctx.message.add_reaction("✅")
            value = stdout.getvalue()

            result = None
            if ret is None:
                if value:
                    result = '```\n{}\n```'.format(value)
                else:
                    try:
                        result = '```\n{}\n```'.format(repr(eval(body, env)))
                    except:
                        pass
            else:
                self._last_result = ret
                result = '```\n{}{}\n```'.format(value, ret)

            if result:
                if len(str(result)) > 1950:
                    await ctx.send("Large output:", file=discord.File(io.BytesIO(result.encode("utf-8")), filename="output.txt"))
                else:
                    await ctx.send(result)

    @commands.group(pass_context=True, invoke_without_command=True)
    @checks.check_permissions_or_owner(administrator=True)
    async def py(self, ctx, *, msg):
        """Python interpreter. See the wiki for more info."""

        if ctx.invoked_subcommand is None:
            env = {
                'bot': self.bot,
                'ctx': ctx,
                'channel': ctx.channel,
                'author': ctx.author,
                'guild': ctx.guild,
                'server': ctx.guild,
                'message': ctx.message,
                '_': self._last_result
            }

            env.update(globals())

            await self.interpreter(env, msg, ctx)


def setup(bot):
    bot.add_cog(Debug(bot))
