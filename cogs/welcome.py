import discord
from discord.ext import commands


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, user):
        welcome = discord.Embed(color=discord.Color.gold())
        welcome.title = "Welcome to the PKHeX Development Projects server, {}!".format(user.name)
        welcome.description = "Don't forget to read <#401014737040834570> and <#438356161218215937> before you start, and keep an eye on <#401017356333088771> for updates!\n\nIf you want to be notified of updates, add the appropriate role in #bot-testing.\n- PKHeX-Plugins (`!toggleplugins`)\n- SysBot.NET (`!togglesysbot`)\n- NHSE / SysBot.AC (`!togglenhse`)"
        await self.bot.welcome_channel.send(user.mention, embed=welcome)


def setup(bot):
    bot.add_cog(Welcome(bot))
