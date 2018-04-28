from discord.ext import commands
import discord.utils
import json

def check_permissions_or_owner(**perms):
    def predicate(ctx):
        msg = ctx.message
        with open("config.json") as c:
            config = json.load(c)
        if msg.author.id == config['owner']:
            return True
        ch = msg.channel
        permissions = ch.permissions_for(msg.author)
        return all(getattr(permissions, perm, None) == value for perm, value in perms.items())

    return commands.check(predicate)