import discord
from discord.ext import commands


class Assignables(commands.Cog):
    """Assignables"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='toggleplugins', aliases=['buildupdates'])
    async def buildupdates(self, ctx):
        """Toggles the PluginsUpdates role"""
        if not ctx.channel.id == 429185857346338827:
            await ctx.message.delete()
            try:
                await ctx.author.send("This command can only be used in <#429185857346338827>. Please move there.")
            except discord.Forbidden:
                pass
            return
        burole = discord.utils.get(ctx.guild.roles, name="PluginsUpdates")
        embed = discord.Embed(color=discord.Color.gold(), timestamp=ctx.message.created_at)
        embed.add_field(name="User", value=ctx.message.author.mention)
        if burole not in ctx.author.roles:
            await ctx.author.add_roles(burole)
            embed.title = "Added PluginsUpdates role"
            await ctx.send("{} : Added Plugin Updates role! You will be notified from now on when a new plugin build is released!".format(ctx.author.mention))
            await self.bot.modlog_channel.send(embed=embed)
        else:
            await ctx.author.remove_roles(burole)
            embed.title = "Removed PluginsUpdates role"
            await ctx.send("{} : Removed Plugin Updates role! You will no longer be notified from now on when a new plugin build is released!".format(ctx.author.mention))
            await self.bot.modlog_channel.send(embed=embed)

    @commands.command(name='togglesysbot')
    async def sysbotupdates(self, ctx):
        """Toggles the SysBotUpdates role"""
        if not ctx.channel.id == 429185857346338827:
            await ctx.message.delete()
            try:
                await ctx.author.send("This command can only be used in <#429185857346338827>. Please move there.")
            except discord.Forbidden:
                pass
            return
        burole = discord.utils.get(ctx.guild.roles, name="SysBotUpdates")
        embed = discord.Embed(color=discord.Color.gold(), timestamp=ctx.message.created_at)
        embed.add_field(name="User", value=ctx.message.author.mention)
        if burole not in ctx.author.roles:
            await ctx.author.add_roles(burole)
            embed.title = "Added SysBotUpdates role"
            await ctx.send("{} : Added SysBot Updates role! You will be notified of any major SysBot news from now on!".format(ctx.author.mention))
            await self.bot.modlog_channel.send(embed=embed)
        else:
            await ctx.author.remove_roles(burole)
            embed.title = "Removed SysBotUpdates role"
            await ctx.send("{} : Removed SysBot Updates role! You will no longer be notified of SysBot news!".format(ctx.author.mention))
            await self.bot.modlog_channel.send(embed=embed)

    @commands.command(name='togglenhse')
    async def nhseupdates(self, ctx):
        """Toggles the NHSEUpdates role"""
        if not ctx.channel.id == 429185857346338827:
            await ctx.message.delete()
            try:
                await ctx.author.send("This command can only be used in <#429185857346338827>. Please move there.")
            except discord.Forbidden:
                pass
            return
        burole = discord.utils.get(ctx.guild.roles, name="NHSEUpdates")
        embed = discord.Embed(color=discord.Color.gold(), timestamp=ctx.message.created_at)
        embed.add_field(name="User", value=ctx.message.author.mention)
        if burole not in ctx.author.roles:
            await ctx.author.add_roles(burole)
            embed.title = "Added NHSEUpdates role"
            await ctx.send("{} : Added NHSE Updates role! You will be notified of any major NHSE news from now on!".format(ctx.author.mention))
            await self.bot.modlog_channel.send(embed=embed)
        else:
            await ctx.author.remove_roles(burole)
            embed.title = "Removed NHSEUpdates role"
            await ctx.send("{} : Removed NHSE Updates role! You will no longer be notified of NHSE news!".format(ctx.author.mention))
            await self.bot.modlog_channel.send(embed=embed)

    @commands.command(name='togglepkhex')
    async def pkhexupdates(self, ctx):
        """Toggles the PKHeXUpdates role"""
        if not ctx.channel.id == 429185857346338827:
            await ctx.message.delete()
            try:
                await ctx.author.send("This command can only be used in <#429185857346338827>. Please move there.")
            except discord.Forbidden:
                pass
            return
        burole = discord.utils.get(ctx.guild.roles, name="PKHeXUpdates")
        embed = discord.Embed(color=discord.Color.gold(), timestamp=ctx.message.created_at)
        embed.add_field(name="User", value=ctx.message.author.mention)
        if burole not in ctx.author.roles:
            await ctx.author.add_roles(burole)
            embed.title = "Added PKHeXUpdates role"
            await ctx.send("{} : Added PKHeX Updates role! You will be notified of any major PKHeX news from now on!".format(ctx.author.mention))
            await self.bot.modlog_channel.send(embed=embed)
        else:
            await ctx.author.remove_roles(burole)
            embed.title = "Removed PKHeXUpdates role"
            await ctx.send("{} : Removed PKHeX Updates role! You will no longer be notified of PKHeX news!".format(ctx.author.mention))
            await self.bot.modlog_channel.send(embed=embed)

    @commands.command(name='toggleweeb')
    async def weebrole(self, ctx):
        """Toggles the weeb role"""
        if not ctx.channel.id == 429185857346338827:
            await ctx.message.delete()
            try:
                await ctx.author.send("This command can only be used in <#429185857346338827>. Please move there.")
            except discord.Forbidden:
                pass
            return
        burole = discord.utils.get(ctx.guild.roles, name="weeb")
        embed = discord.Embed(color=discord.Color.gold(), timestamp=ctx.message.created_at)
        embed.add_field(name="User", value=ctx.message.author.mention)
        if burole not in ctx.author.roles:
            await ctx.author.add_roles(burole)
            embed.title = "Added the weeb role"
            await ctx.send("{} : Added the weeb role! You can now access <#474763733537914882>!".format(ctx.author.mention))
            await self.bot.modlog_channel.send(embed=embed)
        else:
            await ctx.author.remove_roles(burole)
            embed.title = "Removed the weeb role"
            await ctx.send("{} : Removed the weeb role! You will no longer be able to access the weeb-spoilers channel!".format(ctx.author.mention))
            await self.bot.modlog_channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Assignables(bot))
