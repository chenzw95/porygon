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
        self._last_result = None
        self.redirection_clock_task = bot.loop.create_task(self.redirection_clock())

    @commands.command()
    @checks.check_permissions_or_owner(administrator=True)
    async def rehash(self, ctx):
        """Reloads bot configuration."""
        logger.info("Reloading configuration...")
        try:
            with open("config.json") as c:
                config = json.load(c)
            for channel, cid in config['channels'].items():
                setattr(self.bot, "{}_channel".format(channel), self.bot.main_server.get_channel(cid))
        except Exception as e:
            await ctx.send("⚠ Operation failed!\n```\n{}: {}```".format(type(e).__name__, e))
            logger.exception(e)
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
            logger.exception(e)

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
            logger.exception(e)

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
            logger.exception(e)

    @commands.command(aliases=['ri'])
    @commands.guild_only()
    async def roleinfo(self, ctx, role: discord.Role):
        embed = discord.Embed(title="Role information", color=role.color, timestamp=ctx.message.created_at)
        embed.add_field(name="Name", value=role.name).add_field(name="ID", value=role.id)
        embed.add_field(name="Hoisted", value=role.hoist, inline=False).add_field(name="Mentionable", value=role.mentionable)
        await ctx.send(embed=embed)

    @commands.command(aliases=['ui'])
    @commands.guild_only()
    async def userinfo(self, ctx, raw_member=None):
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
        embed.add_field(name="Roles", value=", ".join([str(role) for role in member.roles[1:]]), inline=False)
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
            raise error  # This will print to console (only)

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
            await ctx.send('```\n{}{}\n```'.format(value, traceback.format_exc()))
        else:
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
                    url = await hastebin(str(result).strip("`"), self.bot.session)
                    result = self.bot.bot_prefix + 'Large output. Posted to Hastebin: %s' % url
                    await ctx.send(result)

                else:
                    await ctx.send(result)
            else:
                await ctx.send("```\n```")

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


    # Save last [p]py cmd/script.
    @py.command(pass_context=True)
    @checks.check_permissions_or_owner(administrator=True)
    async def save(self, ctx, *, msg):
        """Save the code you last ran. Ex: [p]py save stuff"""
        msg = msg.strip()[:-4] if msg.strip().endswith('.txt') else msg.strip()
        os.chdir(os.getcwd())
        if not os.path.exists('%s/cogs/utils/temp.txt' % os.getcwd()):
            return await ctx.send(self.bot.bot_prefix + 'Nothing to save. Run a ``>py`` cmd/script first.')
        if not os.path.isdir('%s/cogs/utils/save/' % os.getcwd()):
            os.makedirs('%s/cogs/utils/save/' % os.getcwd())
        if os.path.exists('%s/cogs/utils/save/%s.txt' % (os.getcwd(), msg)):
            await ctx.send(self.bot.bot_prefix + '``%s.txt`` already exists. Overwrite? ``y/n``.' % msg)
            reply = await self.bot.wait_for('message', check=lambda m: m.author == ctx.message.author and (m.content.lower() == 'y' or m.content.lower() == 'n'))
            if reply.content.lower().strip() != 'y':
                return await ctx.send(self.bot.bot_prefix + 'Cancelled.')
            if os.path.exists('%s/cogs/utils/save/%s.txt' % (os.getcwd(), msg)):
                os.remove('%s/cogs/utils/save/%s.txt' % (os.getcwd(), msg))

        try:
            shutil.move('%s/cogs/utils/temp.txt' % os.getcwd(), '%s/cogs/utils/save/%s.txt' % (os.getcwd(), msg))
            await ctx.send(self.bot.bot_prefix + 'Saved last run cmd/script as ``%s.txt``' % msg)
        except:
            await ctx.send(self.bot.bot_prefix + 'Error saving file as ``%s.txt``' % msg)

    # Load a cmd/script saved with the [p]save cmd
    @py.command(aliases=['start'], pass_context=True)
    @checks.check_permissions_or_owner(administrator=True)
    async def run(self, ctx, *, msg):
        """Run code that you saved with the save commmand. Ex: [p]py run stuff parameter1 parameter2"""
        # Like in unix, the first parameter is the script name
        parameters = msg.split()
        save_file = parameters[0] # Force scope
        if save_file.endswith('.txt'):
            save_file = save_file[:-(len('.txt'))] # Temptation to put '.txt' in a constant increases
        else:
            parameters[0] += '.txt' # The script name is always full

        if not os.path.exists('%s/cogs/utils/save/%s.txt' % (os.getcwd(), save_file)):
            return await ctx.send(self.bot.bot_prefix + 'Could not find file ``%s.txt``' % save_file)

        script = open('%s/cogs/utils/save/%s.txt' % (os.getcwd(), save_file)).read()

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'server': ctx.guild,
            'message': ctx.message,
            '_': self._last_result,
            'argv': parameters
        }

        env.update(globals())

        await self.interpreter(env, script, ctx)

    # List saved cmd/scripts
    @py.command(aliases=['ls'], pass_context=True)
    @checks.check_permissions_or_owner(administrator=True)
    async def list(self, ctx, txt: str = None):
        """List all saved scripts. Ex: [p]py list or [p]py ls"""
        try:
            if txt:
                numb = txt.strip()
                if numb.isdigit():
                    numb = int(numb)
                else:
                    await ctx.send(self.bot.bot_prefix + 'Invalid syntax. Ex: ``>py list 1``')
            else:
                numb = 1
            filelist = glob.glob('cogs/utils/save/*.txt')
            if len(filelist) == 0:
                return await ctx.send(self.bot.bot_prefix + 'No saved cmd/scripts.')
            filelist.sort()
            msg = ''
            pages = int(math.ceil(len(filelist) / 10))
            if numb < 1:
                numb = 1
            elif numb > pages:
                numb = pages

            for i in range(10):
                try:
                    msg += filelist[i + (10 * (numb-1))][16:] + '\n'
                except:
                    break

            await ctx.send(self.bot.bot_prefix + 'List of saved cmd/scripts. Page ``%s of %s`` ```%s```' % (numb, pages, msg))
        except Exception as e:
            await ctx.send(self.bot.bot_prefix + 'Error, something went wrong: ``%s``' % e)

    # View a saved cmd/script
    @py.group(aliases=['vi', 'vim'], pass_context=True)
    @checks.check_permissions_or_owner(administrator=True)
    async def view(self, ctx, *, msg: str):
        """View a saved script's contents. Ex: [p]py view stuff"""
        msg = msg.strip()[:-4] if msg.strip().endswith('.txt') else msg.strip()
        try:
            if os.path.isfile('cogs/utils/save/%s.txt' % msg):
                f = open('cogs/utils/save/%s.txt' % msg, 'r').read()
                await ctx.send(self.bot.bot_prefix + 'Viewing ``%s.txt``: ```py\n%s```' % (msg, f.strip('` ')))
            else:
                await ctx.send(self.bot.bot_prefix + '``%s.txt`` does not exist.' % msg)

        except Exception as e:
            await ctx.send(self.bot.bot_prefix + 'Error, something went wrong: ``%s``' % e)

    # Delete a saved cmd/script
    @py.group(aliases=['rm'], pass_context=True)
    @checks.check_permissions_or_owner(administrator=True)
    async def delete(self, ctx, *, msg: str):
        """Delete a saved script. Ex: [p]py delete stuff"""
        msg = msg.strip()[:-4] if msg.strip().endswith('.txt') else msg.strip()
        try:
            if os.path.exists('cogs/utils/save/%s.txt' % msg):
                os.remove('cogs/utils/save/%s.txt' % msg)
                await ctx.send(self.bot.bot_prefix + 'Deleted ``%s.txt`` from saves.' % msg)
            else:
                await ctx.send(self.bot.bot_prefix + '``%s.txt`` does not exist.' % msg)
        except Exception as e:
            await ctx.send(self.bot.bot_prefix + 'Error, something went wrong: ``%s``' % e)    
            
    @commands.command(pass_context=True)
    @checks.check_permissions_or_owner(administrator=True)
    async def redirect(self, ctx):
        """Redirect STDOUT and STDERR to a channel for debugging purposes."""
        sys.stdout = self.stream
        sys.stderr = self.stream
        self.channel = ctx.message.channel
        await ctx.send(self.bot.bot_prefix + "Successfully redirected STDOUT and STDERR to the current channel!")

    @commands.command(pass_context=True)
    @checks.check_permissions_or_owner(administrator=True)
    async def unredirect(self, ctx):
        """Redirect STDOUT and STDERR back to the console for debugging purposes."""
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        self.channel = None
        await ctx.send(self.bot.bot_prefix + "Successfully redirected STDOUT and STDERR back to the console!")

    async def redirection_clock(self):
        await self.bot.wait_until_ready()
        while self is self.bot.get_cog("Debugger"):
            await asyncio.sleep(0.2)
            stream_content = self.stream.getvalue()
            if stream_content and self.channel:
                await self.channel.send("```" + stream_content + "```")
                self.stream = io.StringIO()
                sys.stdout = self.stream
                sys.stderr = self.stream


def setup(bot):
    global logger
    logger = logging.getLogger("cog-debug")
    logger.setLevel(logging.INFO)
    bot.add_cog(Debug(bot))
