import asyncio
import logging

import aiohttp
import discord
from discord.ext import commands


class BuildCog:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(rate=1, per=600.0)
    @commands.has_any_role("Builders", "GitHub Contributors", "Moderators")
    async def build(self, ctx, mgdb_commit: bool=False):
        """
        Initiates a new build on AppVeyor.

        Specify mgdb_commit as true to have the MGDB Downloader download the full database.
        """
        await ctx.trigger_typing()
        async with aiohttp.ClientSession(loop=self.bot.loop, headers={"User-Agent": "Porygon"}) as session:
            headerDict = {'Authorization': 'Bearer {}'.format(self.bot.config['appveyor_token']), 'Content-Type': 'application/json'}
            reqBody = {"accountName": "architdate", "projectSlug": "pkhex-auto-legality-mod", "branch": "master"}
            if mgdb_commit:
                reqBody.update({"environmentVariables": {"latestcommit": "true"}})
            async with session.post('https://ci.appveyor.com/api/builds', headers=headerDict,
                                    json=reqBody) as resp:
                if resp.status == 200:
                    await ctx.message.add_reaction("✅")
                    embed = discord.Embed(color=discord.Color.gold(), timestamp=ctx.message.created_at)
                    embed.title = "Build requested"
                    embed.add_field(name="User", value=ctx.message.author.name)
                    if mgdb_commit:
                        embed.add_field(name="Notice", value="This build will download the entire (non-release version) MGDB.")
                    else:
                        embed.add_field(name="Notice", value="This build will download the latest release version of MGDB.")                        
                    await self.bot.builds_channel.send(embed=embed)
                else:
                    response = await resp.text()
                    logger.error("Build request returned HTTP {}: {}".format(resp.status, response))
                    await ctx.send("⚠️ Request failed. Details have been logged to console.")

    @build.error
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


def setup(bot):
    global logger
    logger = logging.getLogger("cog-build")
    logger.setLevel(logging.INFO)
    bot.add_cog(BuildCog(bot))
