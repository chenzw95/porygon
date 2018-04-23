import json
import logging

import discord
from discord.ext import commands

from .utils import checks


class Mod:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("porygon.{}".format(__name__))

    def add_restriction(self, member, type, expiry=0):
        mid = str(member.id)
        with open("restrictions.json", "r") as f:
            restrictions_db = json.load(f)
        if not restrictions_db.get(mid):
            restrictions_db[mid] = {}
        if not restrictions_db[mid].get(type):
            restrictions_db[mid][type] = expiry
        with open("restrictions.json", "w") as f:
            json.dump(restrictions_db, f, indent=4)

    def remove_restriction(self, member, type):
        mid = str(member.id)
        with open("restrictions.json", "r") as f:
            restrictions_db = json.load(f)
        if not restrictions_db.get(mid):
            # This should not be happening
            restrictions_db[mid] = {}
        restrictions_db[mid].pop(type, None)
        with open("restrictions.json", "w") as f:
            json.dump(restrictions_db, f, indent=4)

    async def on_member_join(self, member):
        embed = discord.Embed(color=discord.Color.green())
        embed.title = "New member"
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Joined at", value=member.joined_at.__format__('%A, %d. %B %Y @ %H:%M:%S'))
        embed.add_field(name="Created at", value=member.created_at.__format__('%A, %d. %B %Y @ %H:%M:%S'))
        await self.bot.modlog_channel.send(embed=embed)

    async def on_member_remove(self, member):
        embed = discord.Embed(color=discord.Color.red())
        embed.title = "Member left"
        embed.add_field(name="User", value=member.mention)
        await self.bot.modlog_channel.send(embed=embed)

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
        embed.title = "Kicked user"
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Action taken by", value=ctx.author.name)
        if member:
            if author.top_role.position < member.top_role.position + 1:
                return await ctx.send("⚠ Operation failed!\nThis cannot be allowed as you are not above the member in role hierarchy.")
            else:
                await member.kick(reason=reason)
                return_msg = "Kicked user: {}".format(member.mention)
                if reason:
                    return_msg += " for reason `{}`".format(reason)
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
        embed.title = "Banned user"
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Action taken by", value=ctx.author.name)
        if member:
            if author.top_role.position < member.top_role.position + 1:
                return await ctx.send("⚠ Operation failed!\nThis cannot be allowed as you are not above the member in role hierarchy.")
            else:
                await member.ban(reason=reason)
                return_msg = "Banned user: {}".format(member.mention)
                if reason:
                    return_msg += " for reason `{}`".format(reason)
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
        self.add_restriction(member, "mute")
        await member.add_roles(self.bot.muted_role, reason=reason)
        await ctx.send("{} has now been muted.".format(member.mention))
        msg = "🤐 **Muted**: {} by {} ({})".format(member.mention, ctx.author.mention, member.id)
        msg += "\nDuration: Indefinite"
        if reason:
            msg += "\nReason: {}".format(reason)
        else:
            msg += "\nReason: *no reason specified*"
        await self.bot.modlog_channel.send(msg)

    @commands.command()
    @checks.check_permissions_or_owner(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmutes a member."""
        self.remove_restriction(member, "mute")
        await member.remove_roles(self.bot.muted_role)
        await ctx.send("{} can now speak again.".format(member.mention))
        msg = "🔉 **Unmute**: {} by {} ({})".format(member.mention, ctx.author.mention, member.id)
        await self.bot.modlog_channel.send(msg)

    @kick.error
    @ban.error
    async def kick_handler(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, commands.BadArgument):
            await ctx.send("Member could not be found.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("⚠ I don't have the permissions to do this.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("{} You don't have permission to use this command.".format(ctx.message.author.mention))

    @promote.error
    async def promote_handler(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, commands.BadArgument):
            await ctx.send("{} Member could not be found! Usage of this command is as follows ```!promote <member> <role>```".format(ctx.message.author.mention))
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("{} You don't have permission to use this command.".format(ctx.message.author.mention))


def setup(bot):
    bot.add_cog(Mod(bot))
