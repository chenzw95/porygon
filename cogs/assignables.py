import discord
from discord.ext import commands

class Assignables:
    """Assignables"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='toggleupdates', aliases=['buildupdates'])
    async def buildupdates(self, ctx):
        """Toggles the BuildUpdates role"""
        burole = discord.utils.get(ctx.guild.roles, name="BuildUpdates")
        embed = discord.Embed(color=discord.Color.gold(), timestamp=ctx.message.created_at)
        embed.add_field(name="User", value=ctx.message.author.mention)
        if burole not in ctx.author.roles:
            await ctx.author.add_roles(burole)
            embed.title = "Added BuildUpdates role"
            await ctx.send("{} : Added Build Updates role! You will be notified from now on when a new build is released!".format(ctx.author.mention))
            await self.bot.modlog_channel.send(embed=embed)
        else:
            await ctx.author.remove_roles(burole)
            embed.title = "Removed BuildUpdates role"
            await ctx.send("{} : Removed Build Updates role! You will no longer be notified from now on when a new build is released!".format(ctx.author.mention))
            await self.bot.modlog_channel.send(embed=embed)

def setup(bot):
    bot.add_cog(Assignables(bot))