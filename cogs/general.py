import discord
from discord.ext import commands
import json

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        target_id = member.guild.id
        with open(self.bot.data_file, 'r') as f:
            guilds_dict = json.load(f)
            for guild in guilds_dict:
                if int(guild) == target_id:
                    target_guild = guilds_dict[guild]
                    break

        if target_guild is not None:
            if 'default_role' in target_guild:
                role_name = target_guild['default_role']
                role = discord.utils.get(member.guild.roles, name=role_name)
                await member.add_roles(role)
            else:
                pass
        else:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        name = member.display_name
        for channel in member.guild.text_channels:
            if channel.permissions_for(member.guild.me).send_messages:
                embed = discord.Embed(title=f"{name} has left {channel.guild.name}!")
                await channel.send(embed=embed)
                break

async def setup(bot):
    await bot.add_cog(General(bot))
    print(f'General Cog is being loaded')

def teardown(bot):
    print(f'General Cog is being removed')
