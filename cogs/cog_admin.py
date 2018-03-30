import json
import logging

from discord.ext import commands


class CogAdminCog:
    def __init__(self, bot):
        self.bot = bot

    def check_permissions_or_owner(**perms):
        def predicate(ctx):
            with open("config.json") as c:
                config = json.load(c)
            msg = ctx.message
            if str(msg.author.id) == config['owner']:
                return True
            ch = msg.channel
            permissions = ch.permissions_for(msg.author)
            return all(getattr(permissions, perm, None) == value for perm, value in perms.items())

        return commands.check(predicate)

    @commands.command()
    @check_permissions_or_owner(administrator=True)
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
    @check_permissions_or_owner(administrator=True)
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
    @check_permissions_or_owner(administrator=True)
    async def unload(self, ctx, module: str):
        if module[0:5] != "cogs.":
            module = "cogs." + module
        if module == "cogs.cog_admin":
            return await ctx.send("⛔ You may not unload this!")
        try:
            self.bot.unload_extension(module)
            await ctx.send("✅ Extension unloaded.")
        except Exception as e:
            await ctx.send("⚠ Operation failed!\n```\n{}: {}```".format(type(e).__name__, e))
            logger.exception(e)


def setup(bot):
    global logger
    logger = logging.getLogger("cog-admin")
    logger.setLevel(logging.INFO)
    bot.add_cog(CogAdminCog(bot))