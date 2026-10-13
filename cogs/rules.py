import json
import logging
import time

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
        msg = await self.bot.rules_channel.fetch_message(730257788894445659)  # Last non-bot message in channel
        async for message in self.bot.rules_channel.history(limit=100, oldest_first=True, after=msg):
            if message.author != self.bot.user:
                continue
            if counter < len(messages):
                if message.embeds and message.embeds[0].title == messages[counter].title \
                    and message.embeds[0].description == messages[counter].description \
                        and message.embeds[0].footer.text == messages[counter].footer.text:
                    counter += 1
                    continue
                time.sleep(2)  # avoid rate limits
                await message.edit(embed=messages[counter])
                counter += 1
            else:
                await message.delete()
        for message in messages[counter:]:
            time.sleep(2)  # avoid rate limits
            await self.bot.rules_channel.send(embed=message)

    @commands.hybrid_group(invoke_without_command=True)
    async def rules(self, ctx):
        await ctx.send_help(ctx.command)

    @rules.command()
    @commands.has_any_role("Moderators")
    async def add(self, ctx):
        if ctx.interaction is None:
            return await ctx.send("Please use `/rules add` to add an entry.")
        await ctx.interaction.response.send_modal(RulesAddModal(self))

    @rules.command(aliases=['del'])
    @commands.has_any_role("Moderators")
    async def delete(self, ctx, rules_id: int = 0):
        if rules_id == 0:
            return await ctx.send("⚠ Rule entry ID is required.")
        with open("rules.json", "r") as f:
            rules_db = json.load(f)
        try:
            rules_db.pop(rules_id - 1)
        except IndexError:
            return await ctx.send("⚠ No such entry exists.")
        with open("rules.json", "w") as f:
            json.dump(rules_db, f, indent=4)
        await ctx.send("✅ Entry deleted.")
        self.bot.loop.create_task(self.update_rules())

    @rules.command(aliases=['modify'])
    @commands.has_any_role("Moderators")
    async def edit(self, ctx, rules_id: int = 0, edit_type: str = "d"):
        if ctx.interaction is None:
            return await ctx.send("Please use `/rules edit` to edit an entry.")
        if rules_id == 0:
            return await ctx.send("⚠ Rule entry ID is required.")
        if not edit_type or not(edit_type[0] == "r" or edit_type[0] == "d"):
            return await ctx.send("⚠ Unknown return type. Acceptable arguments are: `rule`, `description` (default).")
        with open("rules.json", "r") as f:
            rules_db = json.load(f)
        try:
            entry = rules_db[rules_id - 1]
        except IndexError:
            return await ctx.send("⚠ No such entry exists.")
        edit_type_readable = {
            "r": "rule",
            "d": "description"
        }
        field_index = 0 if edit_type[0] == "r" else 1
        await ctx.interaction.response.send_modal(
            RulesEditModal(self, rules_id, field_index, edit_type_readable[edit_type[0]], entry[field_index])
        )

    @rules.command(aliases=['source'])
    async def raw(self, ctx, rules_id: int = 0, return_type: str = "both"):
        if rules_id == 0:
            return await ctx.send("⚠ Rule entry ID is required.")
        if not(return_type[0] == "r" or return_type[0] == "d" or return_type[0] == "b"):
            return await ctx.send("⚠ Unknown return type. Acceptable arguments are: `rule`, `description`, `both` (default).")
        with open("rules.json", "r") as f:
            rules_db = json.load(f)
        try:
            entry = rules_db[rules_id - 1]
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
        await ctx.send("Refreshing rules...")
        self.bot.loop.create_task(self.update_rules())


class RulesAddModal(discord.ui.Modal):
    def __init__(self, cog):
        super().__init__(title="Add rules entry")
        self.cog = cog
        self.rule = discord.ui.TextInput(label="Rule", style=discord.TextStyle.paragraph, max_length=4000)
        self.description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph, max_length=4000)
        self.add_item(self.rule)
        self.add_item(self.description)

    async def on_submit(self, interaction):
        rule = self.rule.value
        description = self.description.value
        if len("RX. __{}__\n{}".format(rule, description)) > 1950:
            return await interaction.response.send_message("⚠ This rule entry is too long.", ephemeral=True)
        with open("rules.json", "r") as f:
            rules_db = json.load(f)
        rules_db.append([rule, description])
        with open("rules.json", "w") as f:
            json.dump(rules_db, f, indent=4)
        await interaction.response.send_message("✅ Entry added.", ephemeral=True)
        self.cog.bot.loop.create_task(self.cog.update_rules())


class RulesEditModal(discord.ui.Modal):
    def __init__(self, cog, rules_id, field_index, field_name, current_value):
        super().__init__(title="Edit rules entry")
        self.cog = cog
        self.rules_id = rules_id
        self.field_index = field_index
        self.content = discord.ui.TextInput(
            label=field_name.capitalize(),
            style=discord.TextStyle.paragraph,
            default=current_value[:4000],
            max_length=4000,
        )
        self.add_item(self.content)

    async def on_submit(self, interaction):
        with open("rules.json", "r") as f:
            rules_db = json.load(f)
        try:
            entry = rules_db[self.rules_id - 1]
        except IndexError:
            return await interaction.response.send_message("⚠ No such entry exists.", ephemeral=True)
        entry[self.field_index] = self.content.value
        if len("RX. __{}__\n{}".format(entry[0], entry[1])) > 1950:
            return await interaction.response.send_message("⚠ This rule entry is too long.", ephemeral=True)
        with open("rules.json", "w") as f:
            json.dump(rules_db, f, indent=4)
        await interaction.response.send_message("✅ Entry modified.", ephemeral=True)
        self.cog.bot.loop.create_task(self.cog.update_rules())


async def setup(bot):
    await bot.add_cog(Rules(bot))
