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

    @commands.command()
    @commands.guild_only()
    async def roleinfo(self, ctx, role: discord.Role):
        embed = discord.Embed(title="Role information", color=role.color, timestamp=ctx.message.created_at)
        embed.add_field(name="Name", value=role.name).add_field(name="ID", value=role.id)
        embed.add_field(name="Hoisted", value=role.hoist, inline=False).add_field(name="Mentionable", value=role.mentionable)


def setup(bot):
    global logger
    logger = logging.getLogger("debug-admin")
    logger.setLevel(logging.INFO)
    bot.add_cog(Debug(bot))