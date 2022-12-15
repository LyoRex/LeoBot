import discord
from discord.ext import commands
import json

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Set the default role for people that join the server", usage="&setdefaultrole <role_name>")
    @commands.guild_only()
    async def setdefaultrole(self, ctx, *, input):
        target_id = ctx.guild.id
        with open(self.bot.data_file, 'r') as f:
            guilds_dict = json.load(f)
        target_guild = guilds_dict[str(target_id)]
        role_name = input.split()[0]
        target_guild['default_role'] = role_name

        with open(self.bot.data_file, 'w', encoding='utf-8') as f:
            json.dump(guilds_dict, f, ensure_ascii=False, indent=4)

        await ctx.send(f"Changed the default role to {role_name}")

async def setup(bot):
    await bot.add_cog(Utility(bot))
    print(f'Utility Cog is being loaded')


def teardown(bot):
    print(f'Utility Cog is being removed')
