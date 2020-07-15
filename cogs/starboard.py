import asyncio
import discord
import typing
import json
import weakref
from discord.ext import commands

from database import config_tbl, starboard_tbl


class Starboard(commands.Cog):
    """
    Adds stuff to the starboard
    """

    def __init__(self, bot):
        self.bot = bot
        self._message_cache = {}
        self._star_queue = weakref.WeakValueDictionary()

    def star_gradient_colour(self, stars):
        p = stars / 13
        if p > 1.0:
            p = 1.0

        red = 255
        green = int((194 * p) + (253 * (1 - p)))
        blue = int((12 * p) + (247 * (1 - p)))
        return (red << 16) + (green << 8) + blue

    def star_emoji(self, stars):
        if 5 > stars >= 0:
            return '\N{WHITE MEDIUM STAR}'
        elif 10 > stars >= 5:
            return '\N{GLOWING STAR}'
        elif 25 > stars >= 10:
            return '\N{DIZZY SYMBOL}'
        else:
            return '\N{SPARKLES}'

    def get_emoji_message(self, message, count):
        emoji = self.star_emoji(count)
        content = '{0} **{1}** {2} ID: {3}'.format(emoji, count, message.channel.mention, message.id)
        embed = discord.Embed(description=message.content)
        if message.embeds:
            data = message.embeds[0]
            if data.type == 'image':
                embed.set_image(url=data.url)

        if message.attachments:
            file = message.attachments[0]
            if file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                embed.set_image(url=file.url)
            else:
                embed.add_field(name='Attachment', value='[{0}]({1})'.format(file.filename, file.url), inline=False)

        embed.add_field(name='Context', value='[Jump!]({0})'.format(message.jump_url), inline=False)
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url_as(format='png'))
        embed.timestamp = message.created_at
        embed.colour = self.star_gradient_colour(count)
        return content, embed

    async def get_message(self, channel, message_id):
        try:
            return self._message_cache[message_id]
        except KeyError:
            try:
                o = discord.Object(id=message_id + 1)
                pred = lambda m: m.id == message_id
                # don't wanna use get_message due to poor rate limit (1/1s) vs (50/1s)
                msg = await channel.history(limit=1, before=o).next()

                if msg.id != message_id:
                    return None

                self._message_cache[message_id] = msg
                return msg
            except Exception:
                return None

    async def update_db(self, message, add_value):
        async with self.bot.engine.acquire() as conn:
            starboard = False
            if message.channel != self.bot.starboard_channel:
                query = starboard_tbl.select().where(starboard_tbl.c.message_id == message.id)
            else:
                query = starboard_tbl.select().where(starboard_tbl.c.starboard_id == message.id)
                starboard = True
            result = await conn.execute(query)
            starcount = self.bot.config['star_count']
            exists = False
            for row in result:
                exists = True
                row_vals = tuple(row.values())
                if starboard:
                    message = await self.get_message(self.bot.main_server.get_channel(row_vals[4]), row_vals[0])
                content, embed = self.get_emoji_message(message, add_value + row_vals[2])
                starboard_message = await self.get_message(self.bot.starboard_channel, row_vals[3])
                if add_value + row_vals[2] > 0:
                    query = starboard_tbl.update().where(starboard_tbl.c.message_id == row_vals[0]).values(star_count=add_value + row_vals[2])
                else:
                    query = starboard_tbl.delete().where(starboard_tbl.c.message_id == row_vals[0])
                await conn.execute(query)
                if add_value + row_vals[2] > 0:
                    await starboard_message.edit(content=content, embed=embed)
                else:
                    await starboard_message.delete()
            star_reactions = self.get_star_reaction_count(message)
            if star_reactions >= starcount and not exists:
                content, embed = self.get_emoji_message(message, star_reactions)
                sent_message = await self.bot.starboard_channel.send(content=content, embed=embed)
                query = starboard_tbl.insert().values(message_id=message.id, author_id=message.author.id, star_count=star_reactions, starboard_id=sent_message.id, channel_id=message.channel.id)
                self._message_cache[sent_message.id] = sent_message
                await conn.execute(query)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.message.type != discord.MessageType.default:
            return
        if str(reaction.emoji) != '⭐':
            return
        star_lock = self._star_queue.get(reaction.message.id)
        if star_lock is None:
            star_lock = asyncio.Lock(loop=self.bot.loop)
            self._star_queue[reaction.message.id] = star_lock
            async with star_lock:
                await self.update_db(reaction.message, 1)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if reaction.message.type != discord.MessageType.default:
            return
        if str(reaction.emoji) != '⭐':
            return
        star_lock = self._star_queue.get(reaction.message.id)
        if star_lock is None:
            star_lock = asyncio.Lock(loop=self.bot.loop)
            self._star_queue[reaction.message.id] = star_lock
            async with star_lock:
                await self.update_db(reaction.message, -1)

    def get_star_reaction_count(self, message):
        reactions = message.reactions
        for r in reactions:
            if str(r.emoji) == '⭐':
                return r.count
        return 0

    @commands.command(name='starboardcount', aliases=['starcount'])
    @commands.has_any_role("Moderators")
    async def starboardcount(self, ctx, stars: int):
        """Modifies the amount of stars needed to add to starboard"""
        if stars <= 0:
            stars = 1
        self.bot.config['star_count'] = stars
        with open('config.json', 'w') as conf:
            data = json.dump(self.bot.config, conf, indent=4)
        await ctx.send("Messages now require {0} star(s) to show up in the starboard.".format(stars))

    @commands.command(name='deletestar', aliases=['delstar'])
    @commands.has_any_role("aww", "Moderators")
    async def deletestar(self, ctx, message_id, clear_stars: typing.Optional[bool] = True):
        async with self.bot.engine.acquire() as conn:
            query = starboard_tbl.select().where(starboard_tbl.c.message_id == message_id)
            result = await conn.execute(query)
            row = await result.fetchone()
            if row:
                original_channel = self.bot.main_server.get_channel(row['channel_id'])
                try:
                    original_message = await original_channel.fetch_message(row['message_id'])
                except discord.NotFound:
                    original_message = None
                starboard_message = await self.bot.starboard_channel.fetch_message(row['starboard_id'])
                if clear_stars:
                    try:
                        if original_message:
                            await original_message.clear_reaction("⭐")
                        await starboard_message.clear_reaction("⭐")
                    except discord.NotFound:
                        pass
                embed = discord.Embed(color=discord.Color.orange(), timestamp=ctx.message.created_at)
                embed.title = "<:nostar:723763060321550407> Message un-starred"
                embed.add_field(name="Original message", value="`{}`".format(starboard_message.embeds[0].description))
                if original_message:
                    context_link = original_message.jump_url
                else:
                    context_link = "*original message deleted*"
                embed.add_field(name="Context", value="{}".format(context_link))
                embed.add_field(name="Un-starred by", value=ctx.author.name)
                await self.bot.modlog_channel.send(embed=embed)
                await conn.execute(starboard_tbl.delete().where(starboard_tbl.c.message_id == row['message_id']))
                await starboard_message.delete()
                return await ctx.send("✅ Message `{}` removed from starboard.".format(row['message_id']))
            else:
                return await ctx.send("❌ Message not found in starboard.")


def setup(bot):
    bot.add_cog(Starboard(bot))
