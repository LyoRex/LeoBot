import discord
from discord.ext import commands, tasks
import time
import os
import json
import random

class WTP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_games = {}
        
        self.pokedex_path = self.bot.pokedex_path

        self.game_loop.start()

        self.game_timeout_length = 30

        self.gen1 = []
        self.gen2 = []
        self.gen3 = []
        self.gen4 = []
        self.gen5 = []
        self.gen6 = []
        self.gen7 = []
        self.gen8 = []

        with open(self.pokedex_path, 'r') as f:
            self.pokedex = json.load(f)

        for p in self.pokedex:
            if p['id'] >= 1 and p['id'] <= 151:
                self.gen1.append(p)
            elif p['id'] >= 152 and p['id'] <= 251:
                self.gen2.append(p)
            elif p['id'] >= 252 and p['id'] <= 386:
                self.gen3.append(p)
            elif p['id'] >= 387 and p['id'] <= 493:
                self.gen4.append(p)
            elif p['id'] >= 494 and p['id'] <= 649:
                self.gen5.append(p)
            elif p['id'] >= 650 and p['id'] <= 721:
                self.gen6.append(p)
            elif p['id'] >= 722 and p['id'] <= 809:
                self.gen7.append(p)
            elif p['id'] >= 810 and p['id'] <= 898:
                self.gen8.append(p)

        self.gen_dexes = []
        self.gen_dexes.append(self.gen1)
        self.gen_dexes.append(self.gen2)
        self.gen_dexes.append(self.gen3)
        self.gen_dexes.append(self.gen4)
        self.gen_dexes.append(self.gen5)
        self.gen_dexes.append(self.gen6)
        self.gen_dexes.append(self.gen7)
        self.gen_dexes.append(self.gen8)

    @commands.command()
    @commands.guild_only()
    async def wtpstart(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        if guild.id in self.guild_games:
            await ctx.send(f"A WTP game has already been started in {guild.name}")
            return
        else:
            await ctx.send(f"Starting a WTP game in {guild.name}")

            gen_args = list(args)

            for arg in gen_args:
                if arg not in ["1","2","3","4","5","6","7","8"]:
                    gen_args.remove(arg)

            if len(gen_args) <= 0:
                gen_args = ["1","2","3","4","5","6","7","8"]

            gen = int(gen_args[random.randint(0, len(gen_args)-1)])
            id = self.gen_dexes[gen - 1][random.randint(0, len(self.gen_dexes[gen-1])-1)]['id']
            self.guild_games[guild.id] = {'game_time_remaining' : self.game_timeout_length, 'channel_id' : channel.id, 'players' : {}, 'generations' : gen_args, 'cur_poke' : id, 'guessed_poke' : False}
            file_path = os.path.join(self.bot.pics_path, 'poke_sills', f"{id}.png")
            with open(file_path, 'rb') as f:
                embed = discord.Embed(title="Who's that Pokemon?", color=0x00ff00)
                picture = discord.File(f, filename="image.png")
                embed.set_image(url="attachment://image.png")
                await channel.send(file=picture, embed=embed)

    @commands.command()
    @commands.guild_only()
    async def wtpend(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        if guild.id not in self.guild_games:
            await ctx.send("No WTP games are ongoing in this server!")
            return
        if self.guild_games[guild.id]['channel_id'] != channel.id:
            await ctx.send("The WTP game in this server is in another channel!")
            return
        await ctx.send("Terminating WTP game...")
        score_message = ""
        for p in self.guild_games[guild.id]['players']:
            score_message += f"{guild.get_member(p)}: {self.guild_games[guild.id]['players'][p]}\n"
        embed = discord.Embed(title="Final Scores", description=score_message)
        await channel.send(embed=embed)
        del self.guild_games[guild.id]

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.channel, discord.channel.TextChannel):
            return
        msg = message.content.lower()
        guild = message.guild
        channel = message.channel
        if guild.id not in self.guild_games:
            return
        if self.guild_games[guild.id]['channel_id'] != channel.id:
            return
        poke_id = self.guild_games[guild.id]['cur_poke']
        pokemon = None
        for p in self.pokedex:
            if p['id'] == poke_id:
                pokemon = p
                break
        if pokemon is None:
            return
        if pokemon['name']['english'].lower() == msg and self.guild_games[guild.id]['guessed_poke'] == False:
            self.guild_games[guild.id]['guessed_poke'] = True
            await channel.send(f"{message.author} guessed the right Pokemon first!")
            if message.author.id in self.guild_games[guild.id]['players']:
                self.guild_games[guild.id]['players'][message.author.id] += 1
            else:
                self.guild_games[guild.id]['players'][message.author.id] = 1
            score_message = ""
            for p in self.guild_games[guild.id]['players']:
                score_message += f"{guild.get_member(p)}: {self.guild_games[guild.id]['players'][p]}\n"
            embed = discord.Embed(title="Current Scores", description=score_message)
            await channel.send(embed=embed)

            gen_args = self.guild_games[guild.id]['generations']

            gen = int(gen_args[random.randint(0, len(gen_args)-1)])
            id = self.gen_dexes[gen - 1][random.randint(0, len(self.gen_dexes[gen-1])-1)]['id']

            self.guild_games[guild.id]['cur_poke'] = id
            self.guild_games[guild.id]['game_time_remaining'] = self.game_timeout_length
            file_path = os.path.join(self.bot.pics_path, 'poke_sills', f"{id}.png")
            with open(file_path, 'rb') as f:
                embed = discord.Embed(title="Who's that Pokemon?", color=0x00ff00)
                picture = discord.File(f, filename="image.png")
                embed.set_image(url="attachment://image.png")
                await channel.send(file=picture, embed=embed)
            self.guild_games[guild.id]['guessed_poke'] = False

    @tasks.loop(seconds=1.0)
    async def game_loop(self):
        if len(self.guild_games) > 0:
            remove_list = []
            for g in self.guild_games:
                self.guild_games[g]['game_time_remaining'] -= 1
                if self.guild_games[g]['game_time_remaining'] <= 0:
                    remove_list.append(g)
            for r in remove_list:
                channel = self.bot.get_channel(self.guild_games[r]['channel_id'])
                await channel.send(f"{self.game_timeout_length} seconds passed without a correct guess. Ending game...")
                poke_id = self.guild_games[r]['cur_poke']
                pokemon = None
                for p in self.pokedex:
                    if p['id'] == poke_id:
                        pokemon = p
                        break
                await channel.send(f"The correct Pokemon was {pokemon['name']['english']}")
                score_message = ""
                for p in self.guild_games[r]['players']:
                    score_message += f"{self.bot.get_guild(r).get_member(p)}: {self.guild_games[r]['players'][p]}\n"
                embed = discord.Embed(title="Final Scores", description=score_message)
                await channel.send(embed=embed)
                del self.guild_games[r]

async def setup(bot):
    await bot.add_cog(WTP(bot))
    print(f'WTP Cog is being loaded')

def teardown(bot):
    print(f'WTP Cog is being removed')
