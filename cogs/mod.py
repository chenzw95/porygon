import discord
import logging

from discord.ext import commands
from .utils import checks


class Mod:
    def __init__(self, bot):
        self.bot = bot

    async def on_member_join(self, user):
        embed = discord.Embed(color=discord.Color.green())
        embed.title = "New Member"
        embed.add_field(name="User", value=user.mention)
        await self.bot.modlog_channel.send(embed=embed)
        welcome = discord.Embed(color=discord.Color.gold())
        welcome.title = "Welcome to the PKHeX Auto Legality Mods server, {}!".format(user.name)
        welcome.description = "Don't forget to read #rules and #announcements. Also if you are interested in the `@BuildUpdates` role, use the !toggleupdates command to get notifications on the latest builds!"
        await self.bot.general_channel.send(user.mention,embed=welcome)

    async def on_member_remove(self, user):
        embed = discord.Embed(color=discord.Color.red())
        embed.title = "Member Left"
        embed.add_field(name="User", value=user.mention)
        await self.bot.modlog_channel.send(embed=embed)

    @commands.command(name='promote', aliases=['addrole'])
    @commands.guild_only()
    @commands.has_any_role("Moderators")
    async def promote(self, ctx, user: discord.Member, role: str):
        """Adds Builder/ GitHub Contributor"""
        if role.lower() in ["builder", "builders"]:
            newrole = discord.utils.get(ctx.guild.roles, name="Builders")
        if role.lower() in ["contributor", "contrib", "github"]:
            newrole = discord.utils.get(ctx.guild.roles, name="GitHub Contributors")
        embed = discord.Embed(color=discord.Color.gold(), timestamp=ctx.message.created_at)
        embed.add_field(name="User", value=user.mention)
        if newrole:
            if newrole not in user.roles:
                await user.add_roles(newrole)
                embed.title = "Added {} role".format(newrole.name)
                await ctx.send("{} : {} role has been added to you!".format(user.mention, newrole.name))
                await self.bot.modlog_channel.send(embed=embed)
            else:
                await ctx.send("{} : {} already has this role!".format(ctx.author.mention, user.name))
        else:
            await ctx.send("⚠ Unrecognised role!")

    @commands.command()
    @checks.check_permissions_or_owner(kick_members=True)
    async def kick(self, ctx, user: discord.Member, *, reason: str = None):
        """Kicks the user"""
        author = ctx.message.author
        embed = discord.Embed(color=discord.Color.red(), timestamp=ctx.message.created_at)
        embed.title = "Kicked User"
        embed.add_field(name="User", value=user.mention)
        if user:
            if author.top_role.position < user.top_role.position + 1:
                return await ctx.send("⚠ Operation failed!\nThis cannot be allowed as you are not above the member in role heirarchy")
            else:
                try:
                    await user.kick(reason=reason)
                    return_msg = "Kicked User: {}".format(user.mention)
                    if reason:
                        return_msg += " for reason `{}`".format(reason)
                    return_msg += "."
                    await ctx.send(return_msg)
                    await self.bot.modlog_channel.send(embed=embed)
                except discord.Forbidden:
                    await ctx.send("Porygon does not have enough permissions to perform a kick")
        else:
            return await ctx.send("Could not find any such user")

    @commands.command()
    @checks.check_permissions_or_owner(ban_members=True)
    async def ban(self, ctx, user:discord.Member, *, reason: str = None):
        """Bans the user"""
        author = ctx.message.author
        embed = discord.Embed(color=discord.Color.red(), timestamp=ctx.message.created_at)
        embed.title = "Banned User"
        embed.add_field(name="User", value=user.mention)
        if user:
            if author.top_role.position < user.top_role.position + 1:
                return await ctx.send("⚠ Operation failed!\nThis cannot be allowed as you are not above the member in role heirarchy")
            else:
                try:
                    await user.ban(reason=reason)
                    return_msg = "Banned User: {}".format(user.mention)
                    if reason:
                        return_msg += " for reason `{}`".format(reason)
                    return_msg += "."
                    await ctx.send(return_msg)
                    await self.bot.modlog_channel.send(embed=embed)
                except discord.Forbidden:
                    await ctx.send("Porygon does not have enough permissions to perform a ban")
        else:
            return await ctx.send("Could not find any such user")

    @kick.error
    @ban.error
    async def kick_handler(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, discord.ext.commands.BadArgument):
            await ctx.send("User could not be found")

    @promote.error
    async def promote_handler(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, discord.ext.commands.BadArgument):
            await ctx.send("{} User could not be found! Usage of this command is as follows ```!promote <user> <role>```".format(ctx.message.author.mention))
        elif isinstance(error, discord.ext.commands.CheckFailure):
            await ctx.send("{} You don't have permission to use this command.".format(ctx.message.author.mention))


def setup(bot):
    global logger
    logger = logging.getLogger("cog-mod")
    logger.setLevel(logging.INFO)
    bot.add_cog(Mod(bot))