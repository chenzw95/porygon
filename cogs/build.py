import asyncio
import logging

import discord
from discord.ext import commands


class BuildCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("porygon.{}".format(__name__))

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(rate=1, per=7200.0)
    @commands.has_any_role("Builders", "GitHub Contributors", "Moderators")
    async def build(self, ctx, mgdb_commit: bool=False):
        """
        Initiates a new build on AppVeyor.
        """
        if mgdb_commit:
            return await ctx.send("🚫 MGDB Downloader behaviour is no longer determined at compile-time.")
        async with ctx.typing():
            headerDict = {'Authorization': 'Bearer {}'.format(self.bot.config['appveyor_token']), 'Content-Type': 'application/json'}
            reqBody = {"accountName": "architdate", "projectSlug": "pkhex-plugins", "branch": "master"}
            async with self.bot.session.post('https://ci.appveyor.com/api/builds', headers=headerDict,
                                    json=reqBody) as resp:
                if resp.status == 200:
                    await ctx.message.add_reaction("✅")
                    embed = discord.Embed(color=discord.Color.gold(), timestamp=ctx.message.created_at)
                    embed.title = "Build requested"
                    embed.add_field(name="User", value=ctx.message.author.mention)
                    await self.bot.builds_channel.send(embed=embed)
                else:
                    response = await resp.text()
                    self.logger.error("Build request returned HTTP {}: {}".format(resp.status, response))
                    await ctx.send("⚠️ Request failed. Details have been logged to console.")

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(rate=1, per=7200.0)
    @commands.has_any_role("Builders", "GitHub Contributors", "Moderators")
    async def buildme(self, ctx, mgdb_commit: bool = False):
        """
        Initiates a new build on AppVeyor. Will not ping those subscribed to build updates.
        """
        if mgdb_commit:
            return await ctx.send("🚫 MGDB Downloader behaviour is no longer determined at compile-time.")
        async with ctx.typing():
            headerDict = {'Authorization': 'Bearer {}'.format(self.bot.config['appveyor_token']),
                          'Content-Type': 'application/json'}
            reqBody = {"accountName": "architdate", "projectSlug": "pkhex-plugins", "branch": "master"}
            envVars = {"notifyall": "false"}
            reqBody["environmentVariables"] = envVars
            async with self.bot.session.post('https://ci.appveyor.com/api/builds', headers=headerDict,
                                    json=reqBody) as resp:
                if resp.status == 200:
                    await ctx.message.add_reaction("✅")
                    embed = discord.Embed(color=discord.Color.gold(), timestamp=ctx.message.created_at)
                    embed.title = "Private build requested"
                    embed.add_field(name="User", value=ctx.message.author.mention)
                    await self.bot.builds_channel.send(embed=embed)
                else:
                    response = await resp.text()
                    self.logger.error("Build request returned HTTP {}: {}".format(resp.status, response))
                    await ctx.send("⚠️ Request failed. Details have been logged to console.")
        check = lambda m: m.channel == self.bot.builds_channel and m.author.name == "BuildBot" and m.author.discriminator == "0000"
        try:
            build_result = await self.bot.wait_for('message', check=check, timeout=300.0)
        except asyncio.TimeoutError:
            return await ctx.send("⚠ Failed to read build notification from AppVeyor.")
        try:
            await ctx.message.author.send("⚙ {0.mention}, your requested build is complete. Details are available in {1.mention}."
                                          .format(ctx.message.author, self.bot.builds_channel))
        except discord.Forbidden:
            await ctx.send("⚙ {0.mention}, your requested build is complete. Details are available in {1.mention}."
                           .format(ctx.message.author, self.bot.builds_channel))

    @build.error
    @buildme.error
    async def rebuild_handler(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, discord.ext.commands.CommandOnCooldown):
            if discord.utils.get(ctx.message.author.roles, name="GitHub Contributors") or discord.utils.get(
                    ctx.message.author.roles, name="Moderators"):
                await ctx.send("A build was last requested {:.0f} seconds ago. Rebuild anyway? `y/n`".format(
                    error.cooldown.per - error.retry_after))
                check = lambda m: m.channel == ctx.message.channel and m.author == ctx.message.author
                try:
                    msg = await self.bot.wait_for('message', check=check, timeout=10.0)
                    if msg.content.lower() == "y":
                        await ctx.reinvoke()
                    else:
                        await ctx.send("Operation cancelled.")
                except asyncio.TimeoutError:
                    await ctx.send("Timed out while waiting for a response.")
            else:
                await ctx.send("This command is on cooldown (executed {:.0f} seconds ago). You will be able to use this command again in {:.0f} seconds.".format(
                        error.cooldown.per - error.retry_after, error.retry_after))
        elif isinstance(error, discord.ext.commands.CheckFailure):
            await ctx.send("{} You don't have permission to use this command.".format(ctx.message.author.mention))

    @commands.command()
    @commands.guild_only()
    @commands.has_any_role("GitHub Contributors", "Moderators")
    async def togglenotify(self, ctx):
        buildupdates = discord.utils.get(self.bot.main_server.roles, name="BuildUpdates")
        mention_flag = not buildupdates.mentionable
        await buildupdates.edit(mentionable=mention_flag, reason="Toggled by {}".format(ctx.author.name))
        await ctx.send("✅ Toggled mentionable flag. New value: {}".format(mention_flag))


def setup(bot):
    bot.add_cog(BuildCog(bot))
