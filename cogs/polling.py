import asyncio
import logging
import requests
from datetime import datetime

import discord
from discord.ext import commands

from database import config_tbl, github_watch_tbl


class CommitTracker:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("porygon.{}".format(__name__))
        self.polling_task = bot.loop.create_task(self.trackCommits())
        self.githubwatch = []

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
                    query = github_watch_tbl.select()
                    result = await conn.execute(query)
                    for row in result:
                        if tuple(row.values()) not in self.githubwatch:
                            self.githubwatch.append(tuple(row.values()))
                for repository in self.githubwatch:
                    self.logger.info("Repository Loaded: " + str(repository))
                    owner = repository[1]
                    repo = repository[0]
                    data = await self.get_latest_commit(owner, repo)
                    commitdata = data[0]
                    commit = commitdata['sha']
                    committime = datetime.strptime(commitdata['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ")
                    if commit != repository[2]:
                        async with self.bot.engine.acquire() as conn:
                            self.githubwatch[self.githubwatch.index(repository)] = (repo, owner, commit)
                            query = github_watch_tbl.update().where(github_watch_tbl.c.name == repo).values(name=repo, owner=owner, commit=commit)
                            await conn.execute(query)
                        self.logger.info("{repo} commit updated to {commit}.".format(repo=repo, commit=commit))
                        embed = discord.Embed(color=7506394, timestamp=committime)
                        embed.title = "[{repo}:master] 1 new commit".format(repo=repo)
                        embed.url = commitdata['html_url']
                        embed.set_author(name=commitdata['author']['login'], icon_url=commitdata['author']['avatar_url'], url=commitdata['author']['html_url'])
                        commitmessage = commitdata['commit']['message'].split("\n\n")[0]
                        if (len(commitmessage) > 50):
                            commitmessage = commitmessage[:47]+"..."
                        embed.description = "[`{shortcommithash}`]({commiturl}) {commitmessage} - {commitauthor}".format(shortcommithash=commit[0:7], commiturl=commitdata['html_url'], commitmessage=commitmessage, commitauthor=commitdata['author']['login'])
                        await self.bot.basecommits_channel.send(embed=embed)
                        if repo == "PKHeX" and owner == "kwsch":
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
            if(len(self.githubwatch) > 0): 
                await asyncio.sleep(self.bot.config['poll_time'] * len(self.githubwatch))
            else: 
                await asyncio.sleep(self.bot.config['poll_time'])

    @commands.command(name='githubwatch', aliases=['gitwatch', 'track'])
    @commands.guild_only()
    @commands.has_any_role("Moderators", "aww")
    async def githubtrack(self, ctx, argument: str, owner=None):
        """
        Tracks a GitHub repository. argument is a mandatory url/reponame
        """
        if owner is None:
            if "github.com/" in argument.lower():
                repo = argument.split("github.com/")[1].split("/")[1]
                owner = argument.split("github.com/")[1].split("/")[0]
            else:
                return await ctx.send("Invalid URL")
        else:
            repo = argument
        # requests used since no benefit an async based request for just a one time command
        request = requests.get("https://github.com/{owner}/{repo}".format(owner=owner, repo=repo))
        if request.status_code != 200:
            return await ctx.send("No such repository exists")
        async with self.bot.engine.acquire() as conn:
            query = github_watch_tbl.insert().values(name=repo, owner=owner, commit="new_commit")
            await conn.execute(query)
            return await ctx.send("{repo} has been added to the GitHub watchlist".format(repo=repo))

    @commands.command(name='githubunwatch', aliases=['gitunwatch', 'untrack'])
    @commands.guild_only()
    @commands.has_any_role("Moderators", "aww")
    async def githubuntrack(self, ctx, argument: str, owner=None):
        """
        Remove tracking of a GitHub repository. argument is a mandatory url/reponame
        """
        if owner is None:
            if "github.com/" in argument.lower():
                repo = argument.split("github.com/")[1].split("/")[1]
                owner = argument.split("github.com/")[1].split("/")[0]
            else:
                return await ctx.send("Invalid URL")
        else:
            repo = argument

        onwatch = False
        watchedval = ("", "", "")
        for repository in self.githubwatch:
            if repository[0] == repo and repository[1] == owner:
                onwatch = True
                watchedval = repository

        if not onwatch:
            return await ctx.send("This repository is not currently on the GitHub watchlist")

        async with self.bot.engine.acquire() as conn:
            query = github_watch_tbl.delete().where(github_watch_tbl.c.name == repo)
            self.githubwatch.remove(watchedval)
            await conn.execute(query)
            return await ctx.send("{repo} has been removed to the GitHub watchlist".format(repo=repo))


def setup(bot):
    bot.add_cog(CommitTracker(bot))
