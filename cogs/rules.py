import asyncio
import json
import logging
import random

import discord
from discord.ext import commands


class Rules(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("porygon.{}".format(__name__))

    async def update_rules(self):
        with open("rules.json", "r") as f:
            rules_db = json.load(f)
        messages = []
        for rules_id, entry in enumerate(rules_db, start=1):
            embed = discord.Embed(color=discord.Color.red())
            embed.title = "R{}. {}".format(rules_id, entry[0])
            embed.description = entry[1]
            messages.append(embed)
        counter = 0
        predicate = lambda m: m.author == self.bot.user
        msg = await self.bot.rules_channel.fetch_message(730257788894445659)  # Last non-bot message in channel
        async for message in self.bot.rules_channel.history(limit=100, oldest_first=True, after=msg).filter(predicate):
            if counter < len(messages):
                if message.embeds and message.embeds[0].title == messages[counter].title \
                    and message.embeds[0].description == messages[counter].description \
                    and message.embeds[0].footer.text == messages[counter].footer.text:
                    counter += 1
                    continue
                time.sleep(2) # avoid rate limits
                await message.edit(embed=messages[counter])
                counter += 1
            else:
                await message.delete()
        for message in messages[counter:]:
            time.sleep(2) # avoid rate limits
            await self.bot.rules_channel.send(embed=message)

    @commands.group(invoke_without_command=True)
    async def rules(self, ctx):
        await ctx.send_help(ctx.command)

    @rules.command()
    @commands.has_any_role("Moderators")
    async def add(self, ctx):
        random_num = random.randint(1, 9999)
        await ctx.send("Type the rule to be added after this message:\n(note: all rules are automatically underlined)\n\nType `abort-{:04d}` to abort.".format(random_num))
        check = lambda m: m.channel == ctx.message.channel and m.author == ctx.author
        try:
            question = await self.bot.wait_for("message", check=check, timeout=30.0)
            if question.content == "abort-{:04d}".format(random_num):
                return await ctx.send("❌ Canceled by user.")
            random_num = random.randint(1, 9999)
            await ctx.send("Type the rule description after this message:\n\nType `abort-{:04d}` to abort.".format(random_num))
            answer = await self.bot.wait_for("message", check=check, timeout=30.0)
            if answer.content == "abort-{:04d}".format(random_num):
                return await ctx.send("❌ Canceled by user.")
        except asyncio.TimeoutError:
            return await ctx.send("🚫 Timed out while waiting for a response, aborting.")
        if len("RX. __{}__\n{}".format(question.content, answer.content)) > 1950:
            return await ctx.send("⚠ This rule entry is too long.")
        with open("rules.json", "r") as f:
            rules_db = json.load(f)
        rules_db.append([question.content, answer.content])
        with open("rules.json", "w") as f:
            json.dump(rules_db, f, indent=4)
        await ctx.send("✅ Entry added.")
        self.bot.loop.create_task(self.update_rules())

    @rules.command(aliases=['del'])
    @commands.has_any_role("Moderators")
    async def delete(self, ctx, rules_id: int = 0):
        if rules_id == 0:
            return await ctx.send("⚠ Rule entry ID is required.")
        with open("rules.json", "r") as f:
            rules_db = json.load(f)
        try:
            rules_db.pop(rules_id-1)
        except IndexError:
            return await ctx.send("⚠ No such entry exists.")
        with open("rules.json", "w") as f:
            json.dump(rules_db, f, indent=4)
        await ctx.send("✅ Entry deleted.")
        self.bot.loop.create_task(self.update_rules())

    @rules.command(aliases=['modify'])
    @commands.has_any_role("Moderators")
    async def edit(self, ctx, rules_id: int = 0, edit_type: str = "d"):
        if rules_id == 0:
            return await ctx.send("⚠ Rule entry ID is required.")
        if not(edit_type[0] == "r" or edit_type[0] == "d"):
            return await ctx.send("⚠ Unknown return type. Acceptable arguments are: `rule`, `description` (default).")
        with open("rules.json", "r") as f:
            rules_db = json.load(f)
        try:
            rules_db[rules_id-1]
        except IndexError:
            return await ctx.send("⚠ No such entry exists.")
        random_num = random.randint(1, 9999)
        edit_type_readable = {
            "r": "rule",
            "d": "description"
        }
        check = lambda m: m.channel == ctx.message.channel and m.author == ctx.author
        await ctx.send("Enter the new {} content:\n\nType `abort-{:04d}` to abort.".format(edit_type_readable[edit_type[0]], random_num))
        try:
            new_content = await self.bot.wait_for("message", check=check, timeout=30.0)
            if new_content.content == "abort-{:04d}".format(random_num):
                return await ctx.send("❌ Canceled by user.")
        except asyncio.TimeoutError:
            return await ctx.send("🚫 Timed out while waiting for a response, aborting.")
        if edit_type[0] == "r":
            rules_db[rules_id - 1][0] = new_content.content
        elif edit_type[0] == "d":
            rules_db[rules_id - 1][1] = new_content.content
        with open("rules.json", "w") as f:
            json.dump(rules_db, f, indent=4)
        await ctx.send("✅ Entry modified.")
        self.bot.loop.create_task(self.update_rules())

    @rules.command(aliases=['source'])
    async def raw(self, ctx, rules_id: int = 0, return_type: str = "both"):
        if rules_id == 0:
            return await ctx.send("⚠ Rule entry ID is required.")
        if not(return_type[0] == "r" or return_type[0] == "d" or return_type[0] == "b"):
            return await ctx.send("⚠ Unknown return type. Acceptable arguments are: `rule`, `description`, `both` (default).")
        with open("rules.json", "r") as f:
            rules_db = json.load(f)
        try:
            entry = rules_db[rules_id-1]
        except IndexError:
            return await ctx.send("⚠ No such entry exists.")
        if return_type[0] == "r":
            msg = entry[0]
        elif return_type[0] == "d":
            msg = entry[1]
        else:
            msg = "\n\n".join(entry)
        await ctx.send("```\n{}\n```".format(msg))

    @rules.command(aliases=['display'])
    async def view(self, ctx, rules_id: int = 0):
        if rules_id == 0:
            return await ctx.send("⚠ Rule entry ID is required.")
        with open("rules.json", "r") as f:
            rules_db = json.load(f)
        try:
            entry = rules_db[rules_id - 1]
        except IndexError:
            return await ctx.send("⚠ No such entry exists.")
        embed = discord.Embed(color=discord.Color.red())
        embed.title = "R{}. {}".format(rules_id, entry[0])
        embed.description = entry[1]
        await ctx.send(embed=embed)

    @rules.command()
    async def refresh(self, ctx):
        self.bot.loop.create_task(self.update_rules())


def setup(bot):
    bot.add_cog(Rules(bot))
