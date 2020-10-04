import json
from discord.ext import commands

def check_permissions_or_owner(**perms):
    def predicate(ctx):
        msg = ctx.message
        with open("config.json") as c:
            config = json.load(c)
        if msg.author.id == config['owner']:
            return True
        permissions = msg.channel.permissions_for(msg.author)
        return all(getattr(permissions, perm, None) == value for perm, value in perms.items())

    return commands.check(predicate)
