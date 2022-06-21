import discord
import random
from discord.ext import commands

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

    @commands.command()
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

        if any(dad in msg for dad in daddy_list):
            for dad in daddy_list:
                for chill in chill_list:
                    if f"{dad} {chill}" in msg:
                        if os.path.exists("personal_gifs"):
                            await channel.send(file=discord.File("personal_gifs/daddy-chill.gif"))
                            await channel.send(file=discord.File("personal_gifs/wthietj.gif"))
                        else:
                            await channel.send(file=discord.File("gifs/trainchill.gif"))
                            await channel.send(file=discord.File("gifs/wthiet.gif"))

        # if not author.bot:
        #     if "ligma" in msg:
        #         await channel.send("Ligma ballz")
        #     elif "sugma" in msg:
        #         await channel.send("Sugma nuts")
        #     elif "bounce" in msg:
        #         await channel.send("Bounce on ya boi's nuts")
        #     elif "candace" in msg:
        #         await channel.send("Candace dick fit in yo mouf")
        #     elif "gulpin" in msg:
        #         await channel.send("Gulpin down dis dick")
        #     elif "im " in msg:
        #         rest = msg.split("im ",1)[1]
        #         await channel.send(f"Hello {rest}, I'm Dad")
        #     elif "i'm " in msg:
        #         rest = msg.split("i'm ", 1)[1]
        #         await channel.send(f"Hello {rest}, I'm Dad")


def setup(bot):
    bot.add_cog(Ligma(bot))
    print(f'Ligma Cog is being loaded')


def teardown(bot):
    print(f'Ligma Cog is being removed')
