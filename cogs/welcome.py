import discord
from discord.ext import commands


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, user):
        welcome = discord.Embed(color=discord.Color.gold())
        welcome.title = "Welcome to the PKHeX Development Projects server, {}!".format(user.name)
        welcome.description = "Don't forget to read #rules and #announcements. Also if you are interested in the `@PluginsUpdates`, `@SysBotUpdates`, `@PKHeXUpdates` or `@NHSEUpdates` role, use the `!toggleplugins`, `!togglesysbot`, `!togglepkhex`, or `!togglenhse` commands respectively to get notifications on the latest news or builds!"
        await self.bot.welcome_channel.send(user.mention, embed=welcome)

     
def setup(bot):
    bot.add_cog(Welcome(bot))
