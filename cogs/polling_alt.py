import asyncio
import logging
from datetime import datetime

import discord

from database import config_tbl


class CommitTracker:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("porygon.{}".format(__name__))
        self.polling_task = bot.loop.create_task(self.trackCommits())

    def __unload(self):
        self.polling_task.cancel()

    async def get_latest_commit(self, owner, repo):
        url = 'https://api.github.com/repos/{owner}/{repo}/commits?per_page=1'.format(owner=owner, repo=repo)
        async with self.bot.session.get(url) as response:
            return await response.json()

    async def trackCommits(self):
        await self.bot.wait_for_setup()
        while not self.bot.is_closed():
            try:
                async with self.bot.engine.acquire() as conn:
                    query = config_tbl.select(config_tbl.c.value).where(config_tbl.c.name == "basecommit")
                    oldcommit = conn.scalar(query)
                owner = 'kwsch'
                repo = 'PKHeX'
                data = await self.get_latest_commit(owner, repo)
                commitdata = data[0]
                commit = commitdata['sha']
                committime = datetime.strptime(commitdata['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ")
                if commit != oldcommit:
                    self.logger.info("Base PKHeX updated to {}.".format(commit))
                    async with self.bot.engine.acquire() as conn:
                        query = config_tbl.update().where(config_tbl.c.name == "basecommit").values(value=commit)
                        await conn.execute(query)
                    embed = discord.Embed(color=7506394, timestamp=committime)
                    embed.title = "[{repo}:master] 1 new commit".format(repo=repo)
                    embed.url = commitdata['html_url']
                    embed.set_author(name=commitdata['author']['login'], icon_url=commitdata['author']['avatar_url'], url=commitdata['author']['html_url'])
                    commitmessage = commitdata['commit']['message'].split("\n\n")[0]
                    if (len(commitmessage) > 50):
                        commitmessage = commitmessage[:47]+"..."
                    embed.description = "[`{shortcommithash}`]({commiturl}) {commitmessage} - {commitauthor}".format(shortcommithash=commit[0:7], commiturl=commitdata['html_url'], commitmessage=commitmessage, commitauthor=commitdata['author']['login'])
                    await self.bot.basecommits_channel.send(embed=embed)
                    headerDict = {'Authorization': 'Bearer {}'.format(self.bot.config['appveyor_token']),
                                  'Content-Type': 'application/json'}
                    reqBody = {"accountName": "architdate", "projectSlug": "pkhex-auto-legality-mod",
                               "branch": "master"}
                    envVars = {"notifyall": "false"}
                    reqBody["environmentVariables"] = envVars
                    async with self.bot.session.post('https://ci.appveyor.com/api/builds', headers=headerDict,
                                                     json=reqBody) as resp:
                        if resp.status != 200:
                            response = await resp.text()
                            self.logger.error("Build request returned HTTP {}: {}".format(resp.status, response))
            except KeyError:
                self.logger.error("Repo polling failed: {}".format(data))
            except Exception as e:
                self.logger.exception("Something went wrong:")
            await asyncio.sleep(self.bot.config['poll_time'])


def setup(bot):
    bot.add_cog(CommitTracker(bot))
