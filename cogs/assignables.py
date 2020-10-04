import discord
from discord.ext import commands


class Assignables(commands.Cog):
    """Assignables"""

    def __init__(self, bot):
        self.bot = bot

    async def handletoggle(self, ctx, role_name):
        """Handles the role toggling. Returns 0 if the role was applied, 1 if it was removed, or 2 if wrong channel."""
        if not ctx.channel.id == 429185857346338827:
            await ctx.message.delete()
            try:
                await ctx.author.send("This command can only be used in <#429185857346338827>. Please move there.")
            except discord.Forbidden:
                pass
            return 2
        embed = discord.Embed(color=discord.Color.gold(), timestamp=ctx.message.created_at)
        embed.add_field(name="User", value="{}#{} ({})".format(ctx.author.name, ctx.author.discriminator, ctx.author.id))
        embed.add_field(name="Mention", value=ctx.author.mention, inline=False)
        burole = discord.utils.get(ctx.guild.roles, name=role_name)
        if burole not in ctx.author.roles:
            embed.title = f"Added {role_name} role"
            await self.bot.modlog_channel.send(embed=embed)
            await ctx.author.add_roles(burole)
            return 0
        else:
            embed.title = f"Removed {role_name} role"
            await self.bot.modlog_channel.send(embed=embed)
            await ctx.author.remove_roles(burole)
            return 1

    @commands.command(name='toggleplugins', aliases=['buildupdates'])
    async def buildupdates(self, ctx):
        """Toggles the PluginsUpdates role"""
        role_on = await self.handletoggle(ctx, "PluginsUpdates")
        if role_on == 0:
            await ctx.send("{} : Added Plugin Updates role! You will now be notified from now on when a new plugin build is released!".format(ctx.author.mention))
        elif role_on == 1:
            await ctx.send("{} : Removed Plugin Updates role! You will no longer be notified from now on when a new plugin build is released!".format(ctx.author.mention))

    @commands.command(name='togglesysbot')
    async def sysbotupdates(self, ctx):
        """Toggles the SysBotUpdates role"""
        role_on = await self.handletoggle(ctx, "SysBotUpdates")
        if role_on == 0:
            await ctx.send("{} : Added SysBot Updates role! You will now be notified of any major SysBot news from now on!".format(ctx.author.mention))
        elif role_on == 1:
            await ctx.send("{} : Removed SysBot Updates role! You will no longer be notified of SysBot news!".format(ctx.author.mention))

    @commands.command(name='togglenhse')
    async def nhseupdates(self, ctx):
        """Toggles the NHSEUpdates role"""
        role_on = await self.handletoggle(ctx, "NHSEUpdates")
        if role_on == 0:
            await ctx.send("{} : Added NHSE Updates role! You will now be notified of any major NHSE news from now on!".format(ctx.author.mention))
        elif role_on == 1:
            await ctx.send("{} : Removed NHSE Updates role! You will no longer be notified of NHSE news!".format(ctx.author.mention))

    @commands.command(name='togglepkhex')
    async def pkhexupdates(self, ctx):
        """Toggles the PKHeXUpdates role"""
        role_on = await self.handletoggle(ctx, "PKHeXUpdates")
        if role_on == 0:
            await ctx.send("{} : Added PKHeX Updates role! You will now be notified of any major PKHeX news from now on!".format(ctx.author.mention))
        elif role_on == 1:
            await ctx.send("{} : Removed PKHeX Updates role! You will no longer be notified of PKHeX news!".format(ctx.author.mention))

    @commands.command(name='toggleweeb')
    async def weebrole(self, ctx):
        """Toggles the weeb role"""
        role_on = await self.handletoggle(ctx, "weeb")
        if role_on == 0:
            await ctx.send("{} : Added the weeb role! You can now access <#474763733537914882>!".format(ctx.author.mention))
        elif role_on == 1:
            await ctx.send("{} : Removed the weeb role! You will no longer be able to access the weeb-spoilers channel!".format(ctx.author.mention))

    @commands.command(name='togglemovies')
    async def moviesrole(self, ctx):
        """Toggles the Movie Nights! role"""
        role_on = await self.handletoggle(ctx, "Movie Nights!")
        if role_on == 0:
            await ctx.send("{} : Added the Movie Nights! role! You will now be notified of community movie nights!".format(ctx.author.mention))
        elif role_on == 1:
            await ctx.send("{} : Removed the Movie Nights! role! You will no longer be notified of community movie nights!".format(ctx.author.mention))

    @commands.command(name='togglegames')
    async def gamesrole(self, ctx):
        """Toggles the Community Games role"""
        role_on = await self.handletoggle(ctx, "Community Games")
        if role_on == 0:
            await ctx.send("{} : Added the Community Games role! You will now be notified of community games!".format(ctx.author.mention))
        elif role_on == 1:
            await ctx.send("{} : Removed the Community Games role! You will no longer be notified of community games!".format(ctx.author.mention))


def setup(bot):
    bot.add_cog(Assignables(bot))
