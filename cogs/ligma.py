import discord
import random
from discord.ext import commands
import os

ligmas = [
    "Ligma....Ligma balls. HA GOTTEM",
    "Have you been to Sol Con? What's Sol Con you ask? Sol Con deez nuts! HA GOTTEM",
    "Have you heard about what happened to Candace? Who's Candace you ask? Candace dick fit in yo mouf?! HA GOTTEM"
]

daddy_list = [
    "daddy",
    "father",
    "dad",
    "papa",
    "pa"
]

chill_list = [
    "chill",
    "relax",
    "cold",
    "frigid",
    "cool",
    "unwind"
]

class Ligma(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Send a random ligma message", usage="&ligma")
    @commands.guild_only()
    async def ligma(self, ctx):
        msg = random.choice(ligmas)
        await ctx.send(msg)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.channel, discord.channel.TextChannel):
            return
        msg = message.content.lower()
        author = message.author
        channel = message.channel

        if author.bot:
            return

        if any(dad in msg for dad in daddy_list):
            found = False
            for dad in daddy_list:
                if found:
                    break
                for chill in chill_list:
                    if f"{dad} {chill}" in msg:
                        if os.path.exists("personal_gifs"):
                            await channel.send(file=discord.File("personal_gifs/trainchill.gif"))
                            await channel.send(file=discord.File("personal_gifs/wthietj.gif"))
                        else:
                            await channel.send(file=discord.File("gifs/daddy-chill.gif"))
                            await channel.send(file=discord.File("gifs/wthiet.gif"))
                        found = True
                        break

async def setup(bot):
    await bot.add_cog(Ligma(bot))
    print(f'Ligma Cog is being loaded')


def teardown(bot):
    print(f'Ligma Cog is being removed')
