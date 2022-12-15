import discord
from discord.ext import commands, tasks
import time
import os
import json
import random

letters = list(map(chr, range(97, 123)))
upper_letters = list(map(chr, range(65, 91)))

green =         ':green_square:'
black =         ':black_large_square:'
yellow =        ':yellow_square:'
letter_prefix = ':regional_indicator_'

class Wordle(commands.Cog):
    """
    Play Wordle in Discord
    """
    def __init__(self, bot):
        self.bot = bot
        self.max_guesses = 6
        self.guild_games = {}
        self.words = []
        self.text_path = self.bot.wordle_text_path

        self.game_timeout_length = 180

        self.read_words()
        self.game_loop.start()

    def read_words(self):
        with open(self.text_path, 'r') as f:
            read_words = f.readlines()

        self.words = []
        for w in read_words:
            self.words.append(w.strip())

    @commands.command(aliases=["wstart"])
    @commands.guild_only()
    async def wordlestart(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel

        if guild.id in self.guild_games:
            await ctx.send(f"A Wordle game has already been started in **{guild.name}**")
            return

        word = random.choice(self.words).lower()

        self.guild_games[guild.id] = {'player' : member.id, 'channel_id' : channel.id, 'cur_word' : word, 'cur_string' : "", 'num_guesses' : 0, 'letter_effects' : [-2] * 26, 'can_guess' : False, 'game_time_remaining' : self.game_timeout_length}
        await ctx.send(f"Wordle game started in {guild.name} by **{member.display_name}**")
        self.guild_games[guild.id]['can_guess'] = True
        
    @commands.command(aliases=["wend"])
    @commands.guild_only()
    async def wordleend(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        if guild.id not in self.guild_games:
            await ctx.send("No Wordle games are ongoing in this server!")
            return
        if member.id != self.guild_games[guild.id]['player']:
            await ctx.send(f"The Wordle game was started by **{guild.get_member(int(self.guild_games[guild.id]['player']))}**. Only they can end it!")
            return
        if self.guild_games[guild.id]['channel_id'] != channel.id:
            await ctx.send("The Wordle game in this server is in another channel!")
            return
        await ctx.send("Terminating Wordle game...")
        await ctx.send(f"The word was **{self.guild_games[guild.id]['cur_word']}**")
        del self.guild_games[guild.id]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.channel, discord.channel.TextChannel):
            return
        msg = message.content.lower()
        guild = message.guild
        channel = message.channel
        if guild.id not in self.guild_games:
            return
        guild_dict = self.guild_games[guild.id]
        if message.author.id != guild_dict['player']:
            return
        guild_dict['game_time_remaining'] = self.game_timeout_length
        if len(msg) != 5:
            return
        if not msg.isalpha():
            return
        if guild_dict['can_guess'] == False:
            return
        if msg not in self.words:
            return

        guild_dict['can_guess'] = False
        out_str = guild_dict['cur_string']

        guessed_letters = list(msg)
        real_letters = list(guild_dict['cur_word'])
        spots = [-1] * 5
        spot_fills = [-1] * 5

        for i in range(len(guessed_letters)):
            if guessed_letters[i] == real_letters[i]:
                spot_fills[i] = 1
                spots[i] = 1
            else:
                spot_fills[i] = -1
        for i in range(len(guessed_letters)):
            if spots[i] == 1:
                continue
            yellowed = False
            for j in range(len(guessed_letters)):
                if j == i:
                    continue
                if guessed_letters[i] == real_letters[j]:
                    if spots[j] == 0 or spots[j] == 1:
                        continue
                    spot_fills[i] = 0
                    spots[j] = 0
                    yellowed = True
                    break
            if yellowed == False:
                spot_fills[i] = -1
        for s in spot_fills:
            if s == -1:
                out_str += f"{black} "
            elif s == 0:
                out_str += f"{yellow} "
            elif s == 1:
                out_str += f"{green} "
            else:
                pass

        out_str += "\n"

        for c in msg:
            out_str += f"{letter_prefix}{c}: "
        out_str += "\n\n"

        letter_string = ""

        for i in range(len(guessed_letters)):
            for l in range(len(letters)):
                if guessed_letters[i] != letters[l]:
                    continue
                if guild_dict['letter_effects'][l] == -2:
                    if spot_fills[i] == 1:
                        guild_dict['letter_effects'][l] = 1
                    elif spot_fills[i] == 0:
                        guild_dict['letter_effects'][l] = 0
                    elif spot_fills[i] == -1:
                        guild_dict['letter_effects'][l] = -1
                elif guild_dict['letter_effects'][l] == 0:
                    if spot_fills[i] == 1:
                        guild_dict['letter_effects'][l] = 1

        for l in range(len(letters)):
            if guild_dict['letter_effects'][l] == -2:
                letter_string += f"{upper_letters[l]} "
            if guild_dict['letter_effects'][l] == -1:
                letter_string += f"||{upper_letters[l]}|| "
            if guild_dict['letter_effects'][l] == 0:
                letter_string += f"__{upper_letters[l]}__ "
            if guild_dict['letter_effects'][l] == 1:
                letter_string += f"**{upper_letters[l]}** "

        final_string = f"{out_str}{letter_string}\n"

        out_embed = discord.Embed(title=f"Wordle Guesses", description=final_string)

        await channel.send(embed=out_embed)

        guild_dict['cur_string'] = out_str
        guild_dict['num_guesses'] += 1
        if msg == guild_dict['cur_word']:
            await channel.send("YOU GUESSED IT!")
            self.add_to_player_data(str(guild.id), str(self.guild_games[guild.id]['player']), str(guild_dict['num_guesses']))
            del self.guild_games[guild.id]
            return

        if guild_dict['num_guesses'] >= self.max_guesses:
            await channel.send(f"YOU RAN OUT OF GUESSES! The word was **{guild_dict['cur_word']}**")
            self.add_to_player_data(str(guild.id), str(self.guild_games[guild.id]['player']), '0')
            del self.guild_games[guild.id]
            return
            
        guild_dict['can_guess'] = True

    @commands.command(aliases=["wstats"])
    @commands.guild_only()
    async def wordlestats(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel

        target_id = "-1"

        if len(args) == 1:
            target_id = args[0].replace('<@','').replace('>','')
        else:
            target_id = str(member.id)
        with open(self.bot.data_file, 'r') as f:
            guilds_dict = json.load(f)
            data = guilds_dict[str(guild.id)]['wordle_data']
            out_string = ""
            player_data = None
            for p in data:
                if p == target_id:
                    player_data = data[p]
                    break
            if player_data == None:
                return
            total_games = 0
            finished_games = 0
            total_score = 0
            for g in player_data:
                if g == '0':
                    out_string += f"**Failures:** {player_data[g]}\n"
                else:
                    out_string += f"**{g} Guesses:** {player_data[g]}\n"
                    total_score += int(player_data[g]) * int(g)
                    finished_games += int(player_data[g])
                total_games += int(player_data[g])
            out_string += f"**Total Games:** {total_games}\n"
            out_string += f"**Average Score of Solved Games:** {(total_score / finished_games):.2f}"
            stats_embed = discord.Embed(title=f"Wordle Stats for {guild.get_member(int(target_id)).display_name} in {guild.name}", description=out_string)
            await channel.send(embed=stats_embed)

    def add_to_player_data(self, guild_id, member_id, num_guesses):
        with open(self.bot.data_file, 'r') as f:
            guilds_dict = json.load(f)
            if member_id in guilds_dict[guild_id]['wordle_data']:
                if str(num_guesses) in guilds_dict[guild_id]['wordle_data'][member_id]:
                    guilds_dict[guild_id]['wordle_data'][member_id][num_guesses] += 1
                else:
                    guilds_dict[guild_id]['wordle_data'][member_id][num_guesses] = 1
            else:
                guilds_dict[guild_id]['wordle_data'][member_id] = {'0' : 0, '1' : 0, '2' : 0, '3' : 0, '4' : 0, '5' : 0, '6' : 0}
                guilds_dict[guild_id]['wordle_data'][member_id][num_guesses] = 1

        with open(self.bot.data_file, 'w', encoding='utf-8') as f:
            json.dump(guilds_dict, f, ensure_ascii=False, indent=4)


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
                await channel.send(f"{self.game_timeout_length} seconds passed without a guess. Ending game...\nThe correct word was **{self.guild_games[r]['cur_word']}**")
                del self.guild_games[r]


async def setup(bot):
    await bot.add_cog(Wordle(bot))
    print(f'Wordle Cog is being loaded')

def teardown(bot):
    print(f'Wordle Cog is being removed')
