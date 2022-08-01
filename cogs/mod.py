# pylint: disable=no-value-for-parameter
import asyncio
import logging
import re
import json
import time
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
        self.session_banlist = set()
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

    async def add_warning(self, member, rst, issuer):
        with open("warnings.json", "r") as f:
            rsts = json.load(f)
        if str(member.id) not in rsts:
            rsts[str(member.id)] = {"warns": []}
        rsts[str(member.id)]["name"] = str(member)
        timestamp = time.strftime("%Y-%m-%d %H%M%S", time.localtime())
        rsts[str(member.id)]["warns"].append({"issuer_id": issuer.id, "issuer_name":issuer.name, "reason":rst, "timestamp":timestamp})
        with open("warnings.json", "w") as f:
            json.dump(rsts, f)

    async def remove_warning(self, member, count):
        with open("warnings.json", "r") as f:
            rsts = json.load(f)
        if str(member.id) not in rsts:
            return -1
        warn_count = len(rsts[str(member.id)]["warns"])
        if warn_count == 0:
            return -1
        if count > warn_count:
            return -2
        if count < 1:
            return -3
        warn = rsts[str(member.id)]["warns"][count-1]
        embed = discord.Embed(color=discord.Color.dark_red(), title="Deleted Warn: {} on {}".format(count, warn["timestamp"]),
                              description="Issuer: {0[issuer_name]}\nReason: {0[reason]}".format(warn))
        del rsts[str(member.id)]["warns"][count-1]
        with open("warnings.json", "w") as f:
            json.dump(rsts, f)
        return embed

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
        if message.guild == None and message.author.id != self.bot.user.id:
            member = message.author
            embed = discord.Embed(color=discord.Color.gold(), timestamp=datetime.utcnow())
            if message.embeds:
                data = message.embeds[0]
                if data.type == 'image':
                    embed.set_image(url=data.url)
            if message.attachments:
                file = message.attachments[0]
                if file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                    embed.set_image(url=file.url)
                else:
                    embed.add_field(name='Attachment', value='[{0}]({1})'.format(file.filename, file.url), inline=False)
            embed.set_author(name="Message from {}#{}".format(member.display_name, member.discriminator), icon_url=member.avatar_url)
            embed.description = message.clean_content
            embed.set_footer(text="ID: {}".format(member.id))
            await self.bot.mod_channel.send(embed=embed)

        whitelisted_roles = ["Moderators", "aww", "Porygon"]
        author = message.author
        if any(r.name in whitelisted_roles for r in author.roles):
            return

        if author.id in self.session_banlist:
            await message.delete()
            return

        # non alpha numeric characters in message
        def isEnglish(s):
            try:
                s.encode(encoding='utf-8').decode('ascii')
            except UnicodeDecodeError:
                return False
            else:
                return True
        if len(author.roles) == 1 and isEnglish(message.content) == False:
            await author.ban(reason="Non-English characters in message with no author roles", delete_message_days=1)
            await self.bot.modlog_channel.send("Banned user : {}#{} ({}) for non-English characters in message".format(author.name, author.discriminator, author.id))
        
        # crypto scammers
        banlist = [
            r".*https://libra-sale.io.*",
            r".*https://ethway.io.*"
        ]
        for ban in banlist:
            if re.match(ban, message.content.lower()):
                if len(author.roles) == 1:
                    await author.ban(reason="Banlisted quote", delete_message_days=1)
                    await self.bot.modlog_channel.send("Banned user : {} for the following message: {}".format(author.mention, message.content))

        # csgo/other game scammers
        games = [
            "csgo",
            "cs:go",
            "steam",
            "skins",
            "@everyone",
            "free",
            "nitro"
        ]
        banned_sites = ['https://', 'http://', 'http://www.', 'https://www.']
        for game in games:
            if game in message.content.lower() and any(domain in message.content.lower() for domain in banned_sites):
                if len(author.roles) == 1:
                    await author.ban(reason="CSGO Scammer most likely", delete_message_days=1)
                    await self.bot.modlog_channel.send("Banned potential CSGO scammer : {} for the following message: {}".format(author.mention, message.clean_content))
                    
        # everyone + embed
        if "@everyone" in message.content.lower() and len(message.embeds) > 0:
            await author.ban(reason="Likely a promotion", delete_message_days=1)
            await self.bot.modlog_channel.send("Banned potential promotion spammer : {} for the following message: {}".format(author.mention, message.clean_content))
        
        # russian sites
        if re.match(r".*http(.)?:\/\/[^\s]*\.ru.*", message.content.lower()):
            await author.ban(reason="Detected russian site. Preemptively banning incase it is a scam", delete_message_days=1)
            await self.bot.modlog_channel.send("Banned potential russian site spammer : {} for the following message: {}".format(author.mention, message.clean_content))

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

    @commands.command(name="listwarns")
    @commands.guild_only()
    async def listwarns(self, ctx, user:discord.User = None):
        """Lists warnings for a user"""
        if user == None or user == ctx.author:
            user = ctx.author
        elif user and not any(role for role in ctx.author.roles if role.name in ["aww", "Moderators"]):
            raise commands.errors.CheckFailure()
            return
        embed = discord.Embed(color=discord.Color.dark_red())
        embed.set_author(name="Warns for {}".format(user), icon_url=user.avatar_url)
        with open("warnings.json", "r") as f:
            warns = json.load(f)
        try:
            if len(warns[str(user.id)]["warns"]) == 0:
                embed.description = "There are none!"
                embed.color = discord.Color.green()
            else:
                for idx, warn in enumerate(warns[str(user.id)]["warns"]):
                    embed.add_field(name="{}: {}".format(idx + 1, warn["timestamp"]), value="Issuer: {}\nReason: {}".format(warn["issuer_name"], warn["reason"]))
        except KeyError:  # if the user is not in the file
            embed.description = "There are none!"
            embed.color = discord.Color.green()
        await ctx.send(embed=embed)


    @commands.command(name="warn")
    @commands.guild_only()
    @commands.has_any_role("Moderators", "aww")
    async def warn(self, ctx, member:discord.Member, *, reason=""):
        """Warn a user. Staff only."""
        issuer = ctx.message.author
        for role in [self.bot.mods_role, self.bot.owner_role, self.bot.aww_role]:
            if role in member.roles:
                await ctx.send("You cannot warn another staffer!")
                return
        await self.add_warning(member, reason, issuer)
        with open("warnings.json", "r") as f:
            rsts = json.load(f)
            warn_count = len(rsts[str(member.id)]["warns"])
        msg = "You were warned on PKHeX Development server."
        if reason != "":
            msg += " The given reason was : " + reason 
        msg += "\n\nPlease read the rules of the server. This is warn #{}".format(warn_count)
        if warn_count >= 5:
            msg += "\n\nYou were automatically banned due to five or more warnings."
            try:
                try:
                    await member.send(msg)
                except discord.errors.Forbidden:
                    pass # dont fail incase user has blocked the bot
                await member.ban(reason=reason, delete_message_days=0)
            except:
                await ctx.send("No permission to ban the warned member")
        elif warn_count >= 3:
            msg += "\n\nYou were kicked because of this warning. You can join again right away. Reaching 5 warnings will result in an automatic ban. Permanent invite link: https://discord.gg/tDMvSRv."
            try:
                try:
                    await member.send(msg)
                except discord.errors.Forbidden:
                    pass # dont fail incase user has blocked the bot
                await member.kick(reason="Three or Four Warnings")
            except:
                await ctx.send("No permission to kick the warned member")
        elif warn_count <= 2:
            msg += " __The next warn will automatically kick.__"
            try:
                await member.send(msg)
            except discord.errors.Forbidden:
                pass # dont fail incase user has blocked the bot
        msg = "⚠️ **Warned**: {} warned {} (warn #{}) | {}".format(issuer.name, member.mention, warn_count, str(member))
        if reason != "":
            msg += " The given reason is : " + reason
        await ctx.send(msg)
        await self.bot.modlog_channel.send(msg)
    
    @commands.command(name="delwarn")
    @commands.guild_only()
    @commands.has_any_role("Moderators", "aww")
    async def delwarn(self, ctx, member:discord.Member, idx:int):
        """Remove a specific warning from a user. Staff only."""
        returnvalue = await self.remove_warning(member,idx)
        with open("warnings.json", "r") as f:
            rsts = json.load(f)
            warn_count = len(rsts[str(member.id)]["warns"])
        error = isinstance(returnvalue, int)
        if error:
            if returnvalue == -1:
                await ctx.send("{} has no warns!".format(member.mention))
            elif returnvalue == -2:
                await ctx.send("Warn index is higher than warn count ({})!".format(warn_count))
            elif returnvalue == -3:
                await ctx.send("Warn index below 1!")
            return
        else:
            msg = "🗑 **Deleted warn**: {} removed warn {} from {} | {}".format(ctx.message.author.name, idx, member.mention, str(member))
            await ctx.send(msg)
            await self.bot.modlog_channel.send(msg, embed=returnvalue)

    @commands.command(name="clearwarns")
    @commands.guild_only()
    @commands.has_any_role("Moderators", "aww")
    async def clearwarns(self, ctx, member:discord.Member):
        """Clears warns of a specific member"""
        with open("warnings.json", "r") as f:
            warns = json.load(f)
        if str(member.id) not in warns:
            await ctx.send("{} has no warns!".format(member.mention))
            return
        warn_count = len(warns[str(member.id)]["warns"])
        if warn_count == 0:
            await ctx.send("{} has no warns!".format(member.mention))
            return
        warns[str(member.id)]["warns"] = []
        with open("warnings.json", "w") as f:
            json.dump(warns, f)
        await ctx.send("{} no longer has any warns!".format(member.mention))
        msg = "🗑 **Cleared warns**: {} cleared {} warns from {} | {}".format(ctx.message.author.name, warn_count, member.mention, str(member))
        await ctx.send(msg)
        await self.bot.modlog_channel.send(msg)

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
    @checks.check_permissions_or_owner(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kickwarn(self, ctx, member: discord.Member, *, reason: str = None):
        """Kicks a member."""
        author = ctx.message.author
        embed = discord.Embed(color=discord.Color.red(), timestamp=ctx.message.created_at)
        embed.title = "👢 Kicked and warned member"
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Action taken by", value=ctx.author.name)
        if member:
            if author.top_role.position < member.top_role.position + 1:
                return await ctx.send("⚠ Operation failed!\nThis cannot be allowed as you are not above the member in role hierarchy.")
            else:
                await self.add_warning(member, reason, author)
                with open("warnings.json", "r") as f:
                    rsts = json.load(f)
                    warn_count = len(rsts[str(member.id)]["warns"])
                try:
                    user_msg = "You have been kicked and warned from {}. You currently have {} warning(s). The reason given was: `{}`. You may rejoin the server any time you wish: https://discord.gg/tDMvSRv .".format(
                        self.bot.main_server.name, warn_count, reason)
                    if warn_count > 3:
                        user_msg += "Your next regular warning will be an automatic ban!"
                    elif warn_count > 1:
                        user_msg += "Your next regular warning will be an automatic kick!"
                    await member.send(user_msg)
                except discord.Forbidden:
                    # DMs disabled by user
                    pass
                if warn_count < 5:
                    await member.kick(reason=reason)
                    self.kick_counter += 1
                    with open("kick_counter.txt", "w") as f:
                        f.write(str(self.kick_counter))
                    return_msg = "Kicked user: {}".format(member.mention)
                else:
                    await member.ban(reason=reason, delete_message_days=0)
                    return_msg = "Banned user: {}".format(member.mention)
                if reason:
                    return_msg += " for reason `{}`".format(reason)
                    embed.add_field(name="Reason", value=reason)
                return_msg += " | **Warned**: {} warned {} (warn #{}) | {}".format(author.name, member.mention, warn_count, str(member))
                await ctx.send(return_msg)
                await self.bot.modlog_channel.send(embed=embed)

    @commands.command()
    @checks.check_permissions_or_owner(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, user: discord.User, *, reason: str = None):
        """Bans a member/user."""
        embed = discord.Embed(color=discord.Color.red(), timestamp=ctx.message.created_at, title="<:banhammer:437900519822852096> Banned member")
        embed.add_field(name="User", value="{} ({})".format(user.mention, user))
        embed.add_field(name="Action taken by", value=ctx.author.name)
        member = ctx.guild.get_member(user.id)
        if member and ctx.message.author.top_role.position < member.top_role.position + 1:
            return await ctx.send("⚠ Operation failed!\nThis cannot be allowed as you are not above the member in role hierarchy.")
        try:
            await user.send("You have been banned from {}. The reason given was: `{}`.".format(ctx.guild.name, reason))
        except discord.Forbidden:
            pass  # DMs disabled by user
        await ctx.guild.ban(user, reason=reason, delete_message_days=0)
        return_msg = "Banned user: {}".format(user.mention)
        if reason:
            return_msg += " for reason `{}`".format(reason)
            embed.add_field(name="Reason", value=reason)
        return_msg += "."
        await ctx.send(return_msg)
        await self.bot.modlog_channel.send(embed=embed)

    @commands.command()
    @checks.check_permissions_or_owner(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def hackban(self, ctx, user_id: int, *, reason: str = None):
        user = await self.bot.fetch_user(user_id)
        if user:
            await self.ban(ctx, user, reason=reason)

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
