import discord


class Welcome:
    def __init__(self, bot):
        self.bot = bot

    async def on_member_join(self, user):
        welcome = discord.Embed(color=discord.Color.gold())
        welcome.title = "Welcome to the PKHeX Auto Legality Mods server, {}!".format(user.name)
        welcome.description = "Don't forget to read #rules and #announcements. Also if you are interested in the `@BuildUpdates` role, use the !toggleupdates command to get notifications on the latest builds!"
        await self.bot.general_channel.send(user.mention,embed=welcome)

     
def setup(bot):
    bot.add_cog(Welcome(bot))
