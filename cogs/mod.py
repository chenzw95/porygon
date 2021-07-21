# pylint: disable=no-value-for-parameter
import asyncio
import logging
import re
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from sqlalchemy.dialects.mysql import insert
from sqlalchemy import null

from database import restrictions_tbl
from .utils import checks


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("porygon.{}".format(__name__))
        self.expiry_task = bot.loop.create_task(self.check_expiry())
        with open("kick_counter.txt", "r") as f:
            try:
                self.kick_counter = int(f.read())
            except ValueError:
                self.kick_counter = 0

    def cog_unload(self):
        self.expiry_task.cancel()

    async def check_expiry(self):
        await self.bot.wait_for_setup()
        while not self.bot.is_closed():
            try:
                async with self.bot.engine.acquire() as conn:
                    now_datetime = datetime.utcnow()
                    query = restrictions_tbl.select().where(restrictions_tbl.c.expiry <= now_datetime).order_by(
                        restrictions_tbl.c.expiry.desc(), restrictions_tbl.c.user.desc()
                    )
                    async for row in conn.execute(query):
                        member = self.bot.main_server.get_member(row.user)
                        if member is not None:
                            await member.remove_roles(getattr(self.bot, "{}_role".format(row.type), None))
                        embed = discord.Embed(color=discord.Color.dark_orange(), timestamp=now_datetime)
                        embed.title = "🕛 Restriction expired"
                        if member is not None:
                            embed.add_field(name="Member", value=member.mention)
                        embed.add_field(name="Member ID", value=row.user)
                        embed.add_field(name="Role", value=getattr(self.bot, "{}_role".format(row.type), None).name)
                        await self.bot.modlog_channel.send(embed=embed)
                        delete_stmt = restrictions_tbl.delete().where(restrictions_tbl.c.id == row.id)
                        await conn.execute(delete_stmt)
            except Exception:  # pylint: disable=broad-except
                self.logger.exception("Something went wrong:")
            finally:
                await asyncio.sleep(1)

    async def add_restriction(self, member, r_type, expiry=null()):
        async with self.bot.engine.acquire() as conn:
            insert_stmt = insert(restrictions_tbl).values(user=member.id, type=r_type, expiry=expiry)
            on_duplicate_key_stmt = insert_stmt.on_duplicate_key_update(expiry=expiry)
            await conn.execute(on_duplicate_key_stmt)

    async def remove_restriction(self, member, r_type):
        async with self.bot.engine.acquire() as conn:
            delete_stmt = restrictions_tbl.delete().where((restrictions_tbl.c.user == member.id) & (restrictions_tbl.c.type == r_type))
            await conn.execute(delete_stmt)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = discord.Embed(color=discord.Color.green())
        embed.title = "🆕 New member"
        embed.add_field(name="User", value="{}#{} ({})".format(member.name, member.discriminator, member.id))
        embed.add_field(name="Mention", value=member.mention, inline=False)
        embed.add_field(name="Joined at", value=member.joined_at.__format__('%A, %d. %B %Y @ %H:%M:%S'))
        embed.add_field(name="Created at", value=member.created_at.__format__('%A, %d. %B %Y @ %H:%M:%S'))
        async with self.bot.engine.acquire() as conn:
            query = restrictions_tbl.select().where((restrictions_tbl.c.user == member.id) & ((restrictions_tbl.c.expiry > datetime.utcnow()) |
                                                                                              (restrictions_tbl.c.expiry == None)))  # pylint: disable=singleton-comparison
            re_add = []
            async for row in conn.execute(query):
                re_add.append(getattr(self.bot, "{}_role".format(row.type), None))
            if re_add:
                await member.add_roles(*re_add)
                embed.add_field(name="⚠ Restrictions re-applied", value=", ".join([x.name for x in re_add]), inline=False)
        await self.bot.modlog_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        embed = discord.Embed(color=discord.Color.red(), timestamp=datetime.utcnow())
        embed.title = "🚪 Member left"
        embed.add_field(name="User", value="{}#{} ({})".format(member.name, member.discriminator, member.id))
        embed.add_field(name="Mention", value=member.mention, inline=False)
        await self.bot.modlog_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        embed = discord.Embed(color=discord.Color.blue(), timestamp=datetime.utcnow())
        member = message.author
        embed.title = "🗑️ Message deleted"
        embed.add_field(name="Author", value="{}#{} ({})".format(member.name, member.discriminator, member.id))
        embed.add_field(name="Mention", value=member.mention, inline=False)
        embed.add_field(name="Content", value="`{}`".format(message.clean_content))
        embed.add_field(name="Channel", value="{} ({})".format(message.channel.mention, message.channel.id))
        embed.add_field(name="Message created", value=message.created_at.__format__('%A, %d. %B %Y @ %H:%M:%S'))
        if message.edited_at:
            embed.add_field(name="Message edited", value=message.edited_at.__format__('%A, %d. %B %Y @ %H:%M:%S'))
        await self.bot.modlog_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        # crypto scammers
        banlist = [
            r".*https://libra-sale.io.*",
            r".*https://ethway.io.*"
        ]
        for ban in banlist:
            if re.match(ban, message.content.lower()):
                author = message.author
                if len(author.roles) == 1:
                    await author.ban(reason="Banlisted quote", delete_message_days=1)
                    await self.bot.modlog_channel.send("Banned user : {} for the following message: {}".format(author.mention, message.content))
        # csgo/other game scammers
        games = [
            "csgo",
            "steam"
        ]
        for game in games:
            if game in message.content.lower() and "https://" in message.content.lower():
                author = message.author
                if len(author.roles) == 1:
                    await author.ban(reason="CSGO Scammer most likely", delete_message_days=1)
                    await self.bot.modlog_channel.send("Banned potential CSGO scammer : {} for the following message: {}".format(author.mention, message.content))

    @commands.command(name='promote', aliases=['addrole'])
    @commands.guild_only()
    @commands.has_any_role("Moderators")
    async def promote(self, ctx, member: discord.Member, role: str):
        """Adds Builder/ GitHub Contributor"""
        if role.lower() in ["builder", "builders"]:
            newrole = discord.utils.get(ctx.guild.roles, name="Builders")
        if role.lower() in ["contributor", "contrib", "github"]:
            newrole = discord.utils.get(ctx.guild.roles, name="GitHub Contributors")
        if newrole:
            if newrole not in member.roles:
                embed = discord.Embed(color=discord.Color.gold(), timestamp=ctx.message.created_at)
                embed.title = "Role added"
                embed.add_field(name="Target", value=member.mention)
                embed.add_field(name="Role", value=newrole.name)
                embed.add_field(name="Action taken by", value=ctx.author.name)
                await member.add_roles(newrole)
                embed.title = "Added {} role".format(newrole.name)
                await ctx.send("{} : {} role has been added to you!".format(member.mention, newrole.name))
                await self.bot.modlog_channel.send(embed=embed)
            else:
                await ctx.send("{} : {} already has this role!".format(ctx.author.mention, member.name))
        else:
            await ctx.send("⚠ Unrecognised role!")

    @commands.command()
    @checks.check_permissions_or_owner(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = None):
        """Kicks a member."""
        author = ctx.message.author
        embed = discord.Embed(color=discord.Color.red(), timestamp=ctx.message.created_at)
        embed.title = "👢 Kicked member"
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Action taken by", value=ctx.author.name)
        if member:
            if author.top_role.position < member.top_role.position + 1:
                return await ctx.send("⚠ Operation failed!\nThis cannot be allowed as you are not above the member in role hierarchy.")
            else:
                try:
                    await member.send("You have been kicked from {}. The reason given was: `{}`. You may rejoin the server any time you wish: https://discord.gg/tDMvSRv".format(
                        self.bot.main_server.name, reason))
                except discord.Forbidden:
                    # DMs disabled by user
                    pass
                await member.kick(reason=reason)
                self.kick_counter += 1
                with open("kick_counter.txt", "w") as f:
                    f.write(str(self.kick_counter))
                return_msg = "Kicked user: {}".format(member.mention)
                if reason:
                    return_msg += " for reason `{}`".format(reason)
                    embed.add_field(name="Reason", value=reason)
                return_msg += "."
                await ctx.send(return_msg)
                await self.bot.modlog_channel.send(embed=embed)

    @commands.command()
    @checks.check_permissions_or_owner(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = None):
        """Bans a member."""
        author = ctx.message.author
        embed = discord.Embed(color=discord.Color.red(), timestamp=ctx.message.created_at)
        embed.title = "<:banhammer:437900519822852096> Banned member"
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Action taken by", value=ctx.author.name)
        if member:
            if author.top_role.position < member.top_role.position + 1:
                return await ctx.send("⚠ Operation failed!\nThis cannot be allowed as you are not above the member in role hierarchy.")
            else:
                try:
                    await member.send("You have been banned from {}. The reason given was: `{}`.".format(
                        self.bot.main_server.name, reason))
                except discord.Forbidden:
                    # DMs disabled by user
                    pass
                await member.ban(reason=reason, delete_message_days=0)
                return_msg = "Banned user: {}".format(member.mention)
                if reason:
                    return_msg += " for reason `{}`".format(reason)
                    embed.add_field(name="Reason", value=reason)
                return_msg += "."
                await ctx.send(return_msg)
                await self.bot.modlog_channel.send(embed=embed)

    @commands.command()
    @checks.check_permissions_or_owner(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason: str = None):
        """Mutes a member permanently."""
        if ctx.author.top_role.position < member.top_role.position + 1:
            return await ctx.send("⚠ Operation failed!\nThis cannot be allowed as you are not above the member in role hierarchy.")
        await self.add_restriction(member, "mute")
        await member.add_roles(self.bot.mute_role, reason=reason)
        await ctx.send("{} has now been muted.".format(member.mention))
        embed = discord.Embed(color=discord.Color.orange(), timestamp=ctx.message.created_at)
        embed.title = "🤐 Muted member"
        embed.add_field(name="Member", value=member.mention).add_field(name="Member ID", value=member.id)
        embed.add_field(name="Action taken by", value=ctx.author.name)
        embed.add_field(name="Duration", value="Indefinite")
        if not reason:
            reason = "*no reason specified*"
        embed.add_field(name="Reason", value=reason)
        await self.bot.modlog_channel.send(embed=embed)

    @commands.command(aliases=['tmute', 'timemute'])
    @checks.check_permissions_or_owner(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def timedmute(self, ctx, member: discord.Member, duration, *, reason: str = None):
        """Mutes a member temporarily."""
        if ctx.author.top_role.position < member.top_role.position + 1:
            return await ctx.send("⚠ Operation failed!\nThis cannot be allowed as you are not above the member in role hierarchy.")
        timeunits = {
            "s": ["second", 1],
            "m": ["minute", 60],
            "h": ["hour", 3600],
            "d": ["day", 86400]
        }
        bantime = 0
        duration_text = ""
        matches = re.findall("([0-9]+[smhd])", duration)
        if not matches:
            return await ctx.send("⚠ Invalid duration.")
        for match in matches:
            bantime += int(match[:-1]) * timeunits[match[-1]][1]
            duration_text += "{} {}".format(match[:-1], timeunits[match[-1]][0])
            if int(match[:-1]) > 1:
                duration_text += "s"
            duration_text += " "
        duration_text = duration_text.rstrip()
        expiry = datetime.utcnow() + timedelta(seconds=bantime)
        await self.add_restriction(member, "mute", expiry)
        await member.add_roles(self.bot.mute_role, reason=reason)
        await ctx.send("{} has now been muted.".format(member.mention))
        embed = discord.Embed(color=discord.Color.orange(), timestamp=ctx.message.created_at)
        embed.title = "🤐 Muted member"
        embed.add_field(name="Member", value=member.mention).add_field(name="Member ID", value=member.id)
        embed.add_field(name="Action taken by", value=ctx.author.name)
        embed.add_field(name="Duration", value=duration_text)
        embed.add_field(name="Expiry", value="{:%A, %d. %B %Y @ %H:%M:%S}".format(expiry))
        if not reason:
            reason = "*no reason specified*"
        embed.add_field(name="Reason", value=reason)
        await self.bot.modlog_channel.send(embed=embed)

    @commands.command()
    @checks.check_permissions_or_owner(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmutes a member."""
        await self.remove_restriction(member, "mute")
        await member.remove_roles(self.bot.mute_role)
        await ctx.send("{} can now speak again.".format(member.mention))
        embed = discord.Embed(color=discord.Color.dark_green(), timestamp=ctx.message.created_at)
        embed.title = "🔉 Unmuted member"
        embed.add_field(name="Member", value=member.mention).add_field(name="Member ID", value=member.id)
        embed.add_field(name="Action taken by", value=ctx.author.name)
        await self.bot.modlog_channel.send(embed=embed)

    @commands.command()
    @commands.cooldown(rate=3, per=15.0, type=BucketType.user)
    async def report(self, ctx):
        await ctx.send("This incident has been reported to the proper authorities. Thank you for your time.")

    @kick.error
    @ban.error
    @mute.error
    @timedmute.error
    @unmute.error
    async def mod_action_handler(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, commands.BadArgument):
            await ctx.send("❌ Member could not be found.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("⚠ I don't have the permissions to do this.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("{} You don't have permission to use this command.".format(ctx.message.author.mention))
        else:
            if ctx.command:
                await ctx.send("An error occurred while processing the `{}` command.".format(ctx.command.name))
            self.logger.exception(error, exc_info=error)

    @promote.error
    async def promote_handler(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, commands.BadArgument):
            await ctx.send("{} Member could not be found! Usage of this command is as follows ```!promote <member> <role>```".format(ctx.message.author.mention))
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("{} You don't have permission to use this command.".format(ctx.message.author.mention))
        else:
            if ctx.command:
                await ctx.send("An error occurred while processing the `{}` command.".format(ctx.command.name))
            self.logger.exception(error, exc_info=error)


def setup(bot):
    bot.add_cog(Mod(bot))
