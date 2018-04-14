import discord
import aiohttp
import asyncio
import logging
import json, time

from discord.ext import commands
from .utils import checks


class CommitTracker:
    def __init__(self, bot):
        self.bot = bot

    async def get_latest_commit(self, owner, repo):
        url = 'https://api.github.com/repos/{owner}/{repo}/commits?per_page=1'.format(owner=owner, repo=repo)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()

    async def trackCommits(self):
        await self.bot.wait_until_ready()
        oldcommit = self.bot.config['basecommit']
        while True:
            owner = 'kwsch'
            repo = 'PKHeX'
            data = await self.get_latest_commit(owner, repo) 
            try:
                commitdata = json.loads(data)[0]
            except KeyError:
                print(json.loads(data))
            commit = commitdata['sha']
            if commit != oldcommit:
                self.bot.config['basecommit'] = commit
                with open("config.json", 'r+') as conf:
                    conf.seek(0)
                    conf.truncate()
                    json.dump(self.bot.config, conf, indent=4)
                embed = discord.Embed(color=7506394)
                embed.title = "[{repo}:master] 1 new commit".format(repo=repo)
                embed.url = commitdata['html_url']
                embed.set_author(name=commitdata['author']['login'], icon_url=commitdata['author']['avatar_url'], url=commitdata['author']['html_url'])
                embed.description = "[`{shortcommithash}`]({commiturl}) {commitmessage} - {commitauthor}".format(shortcommithash=commit[0:7], commiturl=commitdata['html_url'], commitmessage=commitdata['commit']['message'].split("\n\n")[0], commitauthor=commitdata['author']['login'])
                await self.bot.basecommits_channel.send(embed=embed)
            await asyncio.sleep(self.bot.config['poll_time'])


def setup(bot):
    global logger
    logger = logging.getLogger("cog-debug")
    logger.setLevel(logging.INFO)
    c = CommitTracker(bot)
    bot.loop.create_task(c.trackCommits())
    bot.add_cog(c)
