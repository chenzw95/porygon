import traceback
import datetime
import aiohttp
import copy
import logging
import math
import io
import discord
import copy
from discord.ext import commands
from discord.ext.commands import BucketType

import numpy as np

from PIL import Image, ImageEnhance, ImageSequence


class ImageStats:
    __slots__ = ('dark', 'blurple', 'white', 'pixels')

    BLURPLE = (114, 137, 218, 255)
    BLURPLE_HEX = 0x7289da
    DARK_BLURPLE = (78, 93, 148, 255)
    WHITE = (255, 255, 255, 255)

    PIXEL_COUNT_LIMIT = 3840 * 2160
    MAX_PIXEL_COUNT = 1280 * 720
    MAX_FILE_SIZE = 8 * 1024 * 1024 * 16  # 16M

    COLOUR_BUFFER = 20

    def __init__(self, dark, blurple, white, pixels):
        self.dark = dark
        self.blurple = blurple
        self.white = white
        self.pixels = pixels

    @property
    def total(self):
        return self.dark + self.blurple + self.white

    def percentage(self, value):
        return round(value / self.pixels * 100, 2)

    @classmethod
    def from_image(cls, img):
        arr = np.asarray(img).copy()

        dark = np.all(np.abs(arr - cls.DARK_BLURPLE) < cls.COLOUR_BUFFER, axis=2).sum()
        blurple = np.all(np.abs(arr - cls.BLURPLE) < cls.COLOUR_BUFFER, axis=2).sum()
        white = np.all(np.abs(arr - cls.WHITE) < cls.COLOUR_BUFFER, axis=2).sum()
        pixels = img.size[0] * img.size[1]

        mask = np.logical_and(np.abs(arr - cls.DARK_BLURPLE) >= cls.COLOUR_BUFFER,
                              np.abs(arr - cls.BLURPLE) >= cls.COLOUR_BUFFER,
                              np.abs(arr - cls.WHITE) >= cls.COLOUR_BUFFER)
        mask = np.any(mask, axis=2)

        arr[mask] = (0, 0, 0, 255)

        image_file_object = io.BytesIO()
        Image.fromarray(np.uint8(arr)).save(image_file_object, format='png')
        image_file_object.seek(0)

        return image_file_object, ImageStats(dark, blurple, white, pixels)


class BlurpleCog:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("porygon.{}".format(__name__))
        self.BLURPLE = (114, 137, 218, 255)
        self.BLURPLE_HEX = 0x7289da
        self.DARK_BLURPLE = (78, 93, 148, 255)
        self.WHITE = (255, 255, 255, 255)

        self.PIXEL_COUNT_LIMIT = 3840 * 2160
        self.MAX_PIXEL_COUNT = 1280 * 720
        self.MAX_FILE_SIZE = 8 * 1024 * 1024 * 16  # 16M

        self.COLOUR_BUFFER = 20

    async def collect_image(self, ctx, url, static=False):
        data = io.BytesIO()
        async with self.bot.session.get(url) as resp:
            dat = await resp.read()
            data.write(dat)

        im = Image.open(data)
        frames = []
        for frame in ImageSequence.Iterator(im):
            frames.append(frame.copy())
            if static:
                break
        if im.size[0] * im.size[1] > self.MAX_PIXEL_COUNT:
            aspect = im.size[0] / im.size[1]

            height = math.sqrt(self.MAX_PIXEL_COUNT / aspect)
            width = height * aspect

            if height < im.size[1] and width < im.size[0]:
                for n, frame in enumerate(frames):
                    frames[n] = frame.resize((int(width), int(height)), Image.ANTIALIAS)
        for n, frame in enumerate(frames):
            frames[n] = frame.convert('RGBA')
        return frames, url

    def blurplefy_image(self, img):
        #img = img.convert(mode='L')
        img = ImageEnhance.Contrast(img).enhance(1000)
        img = img.convert(mode='RGBA')

        arr = np.asarray(img).copy()
        arr2 = copy.deepcopy(arr[:,:,3])
        arr[np.any(arr != 255, axis=2)] = self.BLURPLE
        arr[:,:,3] = arr2
        return Image.fromarray(np.uint8(arr))

    @commands.command()
    #@commands.cooldown(rate=1, per=180, type=BucketType.user)
    async def blurple(self, ctx, arg1=None):
        if not arg1:
            member = ctx.author
        else:
            try:
                member = await commands.MemberConverter().convert(ctx, arg1)
            except commands.BadArgument:
                return await ctx.send("❌ User not found. Search terms are case sensitive.")
        if ctx.message.attachments:
            url = ctx.message.attachments[0].url
        else:
            url = member.avatar_url
        frames, url = await self.collect_image(ctx, url, True)
        if frames is None:
            return await ctx.message.add_reaction('\N{CROSS MARK}')

        image, stats = await self.bot.loop.run_in_executor(None, ImageStats.from_image, frames[0])
        image = discord.File(fp=image, filename='image.png')

        embed = discord.Embed(Title="", colour=0x7289DA)
        embed.add_field(name="Total amount of Blurple", value="{}%".format(stats.percentage(stats.total)), inline=False)
        embed.add_field(name="Blurple (rgb(114, 137, 218))", value="{}%".format(stats.percentage(stats.blurple)), inline=True)
        embed.add_field(name="White (rgb(255, 255, 255))", value="{}%".format(stats.percentage(stats.white)), inline=True)
        embed.add_field(name="Dark Blurple (rgb(78, 93, 148))", value="{}%".format(stats.percentage(stats.dark)), inline=True)
        embed.add_field(name="Guide",
                        value="Blurple, White, Dark Blurple = Blurple, White, and Dark Blurple (respectively)\n"
                              "Black = Not Blurple, White, or Dark Blurple",
                        inline=False)
        embed.set_image(url="attachment://image.png")
        embed.set_thumbnail(url=url)
        await ctx.send(embed=embed, file=image)


    @commands.command(aliases=['blu', 'blurplfy', 'blurplefier', 'blurplfygif', 'blurplefiergif', 'blurplefygif'])
    #@commands.cooldown(rate=1, per=180, type=BucketType.user)
    async def blurplefy(self, ctx, arg1=None):
        if not arg1:
            member = ctx.author
        else:
            try:
                member = await commands.MemberConverter().convert(ctx, arg1)
            except commands.BadArgument:
                return await ctx.send("❌ User not found. Search terms are case sensitive.")
        if ctx.message.attachments:
            url = ctx.message.attachments[0].url
        else:
            url = member.avatar_url
        frames, url = await self.collect_image(ctx, url, True)
        if frames is None:
            return await ctx.message.add_reaction('\N{CROSS MARK}')

        if len(frames) > 1:
            gif_loop = int(frames[0].info.get('loop', 0))
            gif_duration = frames[0].info.get('duration')
        else:
            gif_loop = gif_duration = None

        def process_sequence(frames, loop, duration):
            for n, frame in enumerate(frames):
                frames[n] = self.blurplefy_image(frame)

            image_file_object = io.BytesIO()
            if len(frames) > 1:
                isgif = True
                frames[0].save(image_file_object, format='gif', save_all=True, append_images=frames[1:], loop=loop,
                               duration=duration)
            else:
                isgif = False
                frames[0].save(image_file_object, format='png')
            image_file_object.seek(0)

            return isgif, image_file_object

        isgif, image = await self.bot.loop.run_in_executor(None, process_sequence, frames, gif_loop, gif_duration)
        image = discord.File(fp=image, filename='blurple.png' if len(frames) == 1 else 'blurple.gif')

        try:
            embed = discord.Embed(Title="", colour=0x7289DA)
            embed.set_author(name="Blurplefier - makes your image blurple!")
            if isgif:
                embed.set_image(url="attachment://blurple.gif")
            else:
                embed.set_image(url="attachment://blurple.png")
            embed.set_thumbnail(url=url)
            await ctx.send(embed=embed, file=image)
        except discord.errors.DiscordException:
            self.logger.exception("Something went wrong:")


def setup(bot):
    bot.add_cog(BlurpleCog(bot))
