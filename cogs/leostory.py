import discord
from discord.ext import commands, tasks
import asyncio

class LeoStory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_games = {}
        self.timeout_loop.start()
        
    @commands.command(aliases=['lsstart'])
    @commands.guild_only()
    async def leostorystart(self, ctx, *args):
        channel = ctx.channel
        author = ctx.author
        if channel.type != discord.ChannelType.text and channel.type != discord.ChannelType.public_thread:
            return
        if author.bot:
            return
        
        out_msg = "Select the story you want to play:\n"
        out_msg += ">>> 1. First Story\n"
        out_msg += "2. Second Story\n"
        out_msg += "3. Third Story\n"
        await channel.send(out_msg)

        def check(m):
            return m.channel == channel

        try:
            msg = await self.bot.wait_for('message', check=check)
            await channel.send(f'You said {msg.content}!')
        except asyncio.TimeoutError:
            await channel.send("You did not send a response in time. Ending game ...")
        
    @commands.command(aliases=['lsend'])
    @commands.guild_only()
    async def leostoryend(self, ctx, *args):
        pass

    @tasks.loop(seconds=1.0)
    async def timeout_loop(self):
        if len(self.guild_games) < 1:
            return
        remove_list = []
        for g in self.guild_games:
            self.guild_games[g]['game_time_remaining'] -= 1
            if self.guild_games[g]['game_time_remaining'] <= 0:
                remove_list.append(g)
        for r in remove_list:
            channel = self.bot.get_channel(self.guild_games[r]['channel_id'])
            await channel.send(f"{self.guild_games[r]['decision_time_limit']} seconds passed without a response. Ending game...")
            del self.guild_games[r]

async def setup(bot):
    await bot.add_cog(LeoStory(bot))
    print(f'LeoStory Cog is being loaded')

def teardown(bot):
    print(f'LeoStory Cog is being removed')