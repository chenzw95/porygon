import json
import logging
import discord

from discord.ext import commands
from .utils import checks

class Debug:
    def __init__(self, bot):
        self.bot = bot

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


def setup(bot):
    global logger
    logger = logging.getLogger("cog-debug")
    logger.setLevel(logging.INFO)
    bot.add_cog(Debug(bot))
