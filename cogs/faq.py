import json
import logging
import time

import discord
from discord.ext import commands


class Faq(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.faq_aliases = {}
        with open('faq_aliases.json', 'r') as f:
            self.faq_aliases = json.load(f)
        self.logger = logging.getLogger("porygon.{}".format(__name__))

    async def update_faq(self):
        with open("faq.json", "r") as f:
            faq_db = json.load(f)
        messages = []
        for faq_id, entry in enumerate(faq_db, start=1):
            embed = discord.Embed(color=discord.Color.red())
            embed.title = "Q{}. {}".format(faq_id, entry[0])
            embed.description = entry[1]
            aliases = []
            for word, faq in self.faq_aliases.items():
                if faq == faq_id:
                    aliases.append(word)
            if aliases:
                embed.set_footer(text="Aliases: " + ", ".join(aliases))
            messages.append(embed)
        counter = 0
        async for message in self.bot.faq_channel.history(limit=100, oldest_first=True):
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
            await self.bot.faq_channel.send(embed=message)

    @commands.hybrid_group(invoke_without_command=True)
    async def faq(self, ctx):
        await ctx.send_help(ctx.command)

    @faq.command()
    @commands.has_any_role("GitHub Contributors", "Moderators", "aww")
    async def add(self, ctx):
        if ctx.interaction is None:
            return await ctx.send("Please use `/faq add` to add an entry.")
        await ctx.interaction.response.send_modal(FaqAddModal(self))

    @faq.command()
    @commands.has_any_role("GitHub Contributors", "Moderators", "aww")
    async def alias(self, ctx, faq_id: int = 0, *, words: str = ""):
        if faq_id == 0:
            return await ctx.send("⚠ FAQ entry ID is required.")
        for word in words.strip().split():
            self.faq_aliases[word] = faq_id
        with open("faq_aliases.json", "w") as f:
            json.dump(self.faq_aliases, f, indent=4)
        await ctx.send("✅ Alias added/updated.")
        self.bot.loop.create_task(self.update_faq())

    @faq.command()
    @commands.has_any_role("GitHub Contributors", "Moderators", "aww")
    async def delalias(self, ctx, word: str):
        if word not in self.faq_aliases:
            return await ctx.send("⚠ FAQ alias does not exist.")
        del self.faq_aliases[word]
        with open("faq_aliases.json", "w") as f:
            json.dump(self.faq_aliases, f, indent=4)
        await ctx.send("✅ Alias removed.")
        self.bot.loop.create_task(self.update_faq())

    @faq.command()
    async def listaliases(self, ctx, faq_id: int = 0):
        if faq_id == 0:
            return await ctx.send("⚠ FAQ entry ID is required.")
        aliases = []
        for word, faq in self.faq_aliases.items():
            if faq == faq_id:
                aliases.append(word)
        if not aliases:
            return await ctx.send("⚠ No aliases found.")
        await ctx.send("Aliases for FAQ entry {}: {}".format(faq_id, ", ".join(aliases)))

    @faq.command(aliases=['del'])
    @commands.has_any_role("GitHub Contributors", "Moderators", "aww")
    async def delete(self, ctx, faq_id: int = 0):
        if faq_id == 0:
            return await ctx.send("⚠ FAQ entry ID is required.")
        with open("faq.json", "r") as f:
            faq_db = json.load(f)
        try:
            faq_db.pop(faq_id - 1)
            for word, faq in self.faq_aliases.items():
                if faq == faq_id:
                    del self.faq_aliases[word]
                if faq > faq_id:
                    self.faq_aliases[word] = faq - 1
            with open("faq_aliases.json", "w") as f:
                json.dump(self.faq_aliases, f, indent=4)
        except IndexError:
            return await ctx.send("⚠ No such entry exists.")
        with open("faq.json", "w") as f:
            json.dump(faq_db, f, indent=4)
        await ctx.send("✅ Entry deleted.")
        self.bot.loop.create_task(self.update_faq())

    @faq.command(aliases=['modify'])
    @commands.has_any_role("GitHub Contributors", "Moderators", "aww")
    async def edit(self, ctx, faq_id: int = 0, edit_type: str = "a"):
        if ctx.interaction is None:
            return await ctx.send("Please use `/faq edit` to edit an entry.")
        if faq_id == 0:
            return await ctx.send("⚠ FAQ entry ID is required.")
        if not edit_type or not(edit_type[0] == "q" or edit_type[0] == "a"):
            return await ctx.send("⚠ Unknown return type. Acceptable arguments are: `question`, `answer` (default).")
        with open("faq.json", "r") as f:
            faq_db = json.load(f)
        try:
            entry = faq_db[faq_id - 1]
        except IndexError:
            return await ctx.send("⚠ No such entry exists.")
        edit_type_readable = {
            "q": "question",
            "a": "answer"
        }
        field_index = 0 if edit_type[0] == "q" else 1
        await ctx.interaction.response.send_modal(
            FaqEditModal(self, faq_id, field_index, edit_type_readable[edit_type[0]], entry[field_index])
        )

    @faq.command(aliases=['source'])
    async def raw(self, ctx, faq_id: int = 0, return_type: str = "both"):
        if faq_id == 0:
            return await ctx.send("⚠ FAQ entry ID is required.")
        if not(return_type[0] == "q" or return_type[0] == "a" or return_type[0] == "b"):
            return await ctx.send("⚠ Unknown return type. Acceptable arguments are: `question`, `answer`, `both` (default).")
        with open("faq.json", "r") as f:
            faq_db = json.load(f)
        try:
            entry = faq_db[faq_id - 1]
        except IndexError:
            return await ctx.send("⚠ No such entry exists.")
        if return_type[0] == "q":
            msg = entry[0]
        elif return_type[0] == "a":
            msg = entry[1]
        else:
            msg = "\n\n".join(entry)
        await ctx.send("```\n{}\n```".format(msg))

    @faq.command(aliases=['display'])
    async def view(self, ctx, faq_req):
        if faq_req.isnumeric():
            faq_id = int(faq_req)
        elif faq_req in self.faq_aliases:
            faq_id = self.faq_aliases[faq_req]
        else:
            return await ctx.send("⚠ No such entry exists.")
        if faq_id == 0:
            return await ctx.send("⚠ FAQ entry ID is required.")
        with open("faq.json", "r") as f:
            faq_db = json.load(f)
        try:
            entry = faq_db[faq_id - 1]
        except IndexError:
            return await ctx.send("⚠ No such entry exists.")
        embed = discord.Embed(color=discord.Color.red())
        embed.title = "Q{}. {}".format(faq_id, entry[0])
        embed.description = entry[1]
        aliases = []
        for word, faq in self.faq_aliases.items():
            if faq == faq_id:
                aliases.append(word)
        if aliases:
            embed.set_footer(text="Aliases: " + ", ".join(aliases))
        await ctx.send(embed=embed)

    @faq.command()
    async def refresh(self, ctx):
        await ctx.send("Refreshing FAQ...")
        self.bot.loop.create_task(self.update_faq())


class FaqAddModal(discord.ui.Modal):
    def __init__(self, cog):
        super().__init__(title="Add FAQ entry")
        self.cog = cog
        self.question = discord.ui.TextInput(label="Question", style=discord.TextStyle.paragraph, max_length=4000)
        self.answer = discord.ui.TextInput(label="Answer", style=discord.TextStyle.paragraph, max_length=4000)
        self.add_item(self.question)
        self.add_item(self.answer)

    async def on_submit(self, interaction):
        question = self.question.value
        answer = self.answer.value
        if len("❔ QX. __{}__\n{}".format(question, answer)) > 1950:
            return await interaction.response.send_message("⚠ This FAQ entry is too long.", ephemeral=True)
        with open("faq.json", "r") as f:
            faq_db = json.load(f)
        faq_db.append([question, answer])
        with open("faq.json", "w") as f:
            json.dump(faq_db, f, indent=4)
        await interaction.response.send_message("✅ Entry added.", ephemeral=True)
        self.cog.bot.loop.create_task(self.cog.update_faq())


class FaqEditModal(discord.ui.Modal):
    def __init__(self, cog, faq_id, field_index, field_name, current_value):
        super().__init__(title="Edit FAQ entry")
        self.cog = cog
        self.faq_id = faq_id
        self.field_index = field_index
        self.content = discord.ui.TextInput(
            label=field_name.capitalize(),
            style=discord.TextStyle.paragraph,
            default=current_value[:4000],
            max_length=4000,
        )
        self.add_item(self.content)

    async def on_submit(self, interaction):
        with open("faq.json", "r") as f:
            faq_db = json.load(f)
        try:
            entry = faq_db[self.faq_id - 1]
        except IndexError:
            return await interaction.response.send_message("⚠ No such entry exists.", ephemeral=True)
        entry[self.field_index] = self.content.value
        if len("❔ Q{}. __{}__\n{}".format(self.faq_id, entry[0], entry[1])) > 1950:
            return await interaction.response.send_message("⚠ This FAQ entry is too long.", ephemeral=True)
        with open("faq.json", "w") as f:
            json.dump(faq_db, f, indent=4)
        await interaction.response.send_message("✅ Entry modified.", ephemeral=True)
        self.cog.bot.loop.create_task(self.cog.update_faq())


async def setup(bot):
    await bot.add_cog(Faq(bot))
