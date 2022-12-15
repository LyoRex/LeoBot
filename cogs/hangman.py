import discord
from discord.ext import commands
import random
import os
import json
import sys

class Hangman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_games = {}
        self.wrong_limit = 6
        self.hangman_text_path = self.bot.hangman_text_path

    @commands.command(aliases=["hstart"], help="Start a hangman game", usage="&hangmanstart")
    @commands.guild_only()
    async def hangmanstart(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel

        if guild.id in self.guild_games:
            await ctx.send(f"A Hangman game has already been started in {guild.name}")
            return

        with open(self.hangman_text_path, 'r') as f:
            words = f.readlines()

        word = random.choice(words).lower().strip()
        rev = ""
        for char in word:
            rev += "-"
        self.guild_games[guild.id] = {'player' : member.id, 'channel_id' : channel.id, 'cur_word' : word, 'cur_rev' : rev, 'guessed_letters' : [], 'can_guess' : False, 'wrongs_left' : self.wrong_limit}
        await ctx.send(f"Hangman game started in {guild.name} by {member.display_name}")
        output = " ".join([char for char in rev])
        await ctx.send(output)
        self.guild_games[guild.id]['can_guess'] = True

    @commands.command(aliases=["hend"], help="End current hangman game", usage="&hangmanend")
    @commands.guild_only()
    async def hangmanend(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        if guild.id not in self.guild_games:
            await ctx.send("No Hangman games are ongoing in this server!")
            return
        if self.guild_games[guild.id]['channel_id'] != channel.id:
            await ctx.send("The Hangman game in this server is in another channel!")
            return
        await ctx.send("Terminating Wordle game...")
        await ctx.send(f"The word was {self.guild_games[guild.id]['cur_word']}")
        del self.guild_games[guild.id]

    @commands.command(aliases=["hstats"], help="Show hangman game stats for everyone in the server", usage="&hangmanstats")
    @commands.guild_only()
    async def hangmanstats(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel

        with open(self.bot.data_file, 'r') as f:
            guilds_dict = json.load(f)
            data = guilds_dict[str(guild.id)]['hangman_data']
            out_string = ""
            for p in data:
                wins = data[p]['wins']
                losses = data[p]['losses']
                out_string += f"{guild.get_member(int(p))}: {wins}-{losses}\n"
            stats_embed = discord.Embed(title=f"Hangman Stats for {guild.name}", description=out_string)
            await channel.send(embed=stats_embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.channel, discord.channel.TextChannel):
            return
        msg = message.content.lower()
        guild = message.guild
        channel = message.channel
        if len(msg) > 1:
            return
        if not msg.isalpha():
            return
        if guild.id not in self.guild_games:
            return
        guild_dict = self.guild_games[guild.id]
        if message.author.id != guild_dict['player']:
            return
        if msg in guild_dict['guessed_letters']:
            await channel.send(f"You already guessed {msg}")
            return
        if msg in guild_dict['guessed_letters']:
            return
        if guild_dict['can_guess'] == False:
            return
        guild_dict['can_guess'] = False
        guild_dict['guessed_letters'].append(msg)
        new_rev = guild_dict['cur_rev']
        num_in = 0
        for i in range(len(guild_dict['cur_word'])):
            if guild_dict['cur_word'][i] == msg:
                new_rev = new_rev[:i] + msg + new_rev[i+1:]
                num_in += 1
        if num_in == 0:
            guild_dict['wrongs_left'] -= 1
        file_path = os.path.join('pics', 'hangman', f"hangman{6-guild_dict['wrongs_left']}.png")
        guessed_letters = "**Guessed letters:** "
        guessed_vowels = []
        guessed_consonants = []
        for l in guild_dict['guessed_letters']:
            if l in ['a', 'e', 'i', 'o', 'u']:
                guessed_vowels.append(l)
            else:
                guessed_consonants.append(l)
        guessed_vowels.sort()
        guessed_consonants.sort()
        guessed_letters += " ".join(guessed_vowels)
        guessed_letters += " "
        guessed_letters += " ".join(guessed_consonants)
        with open(file_path, 'rb') as f:
            embed = discord.Embed(title=f"There is/are {num_in} {msg}(s) in the word")
            picture = discord.File(f, filename="image.png")
            embed.set_image(url="attachment://image.png")
            guild_dict['cur_rev'] = new_rev
            output = " ".join([char for char in guild_dict['cur_rev']])
            embed.description = output + "\n" + guessed_letters
            await channel.send(file=picture, embed=embed)
        if '-' not in output:
            await channel.send("You guessed it!")
            self.add_win(str(guild.id), str(self.guild_games[guild.id]['player']))
            del self.guild_games[guild.id]
            return
        if guild_dict['wrongs_left'] == 0:
            await channel.send(f"You died! The correct word was _***{guild_dict['cur_word']}***_")
            self.add_loss(str(guild.id), str(self.guild_games[guild.id]['player']))
            del self.guild_games[guild.id]
            return
        guild_dict['can_guess'] = True

    def add_win(self, guild_id, member_id):
        with open(self.bot.data_file, 'r') as f:
            guilds_dict = json.load(f)
            if member_id in guilds_dict[guild_id]['hangman_data']:
                if 'wins' in guilds_dict[guild_id]['hangman_data'][member_id]:
                    guilds_dict[guild_id]['hangman_data'][member_id]['wins'] += 1
                else:
                    guilds_dict[guild_id]['hangman_data'][member_id]['wins'] = 1
            else:
                guilds_dict[guild_id]['hangman_data'][member_id] = {'wins' : 1, 'losses' : 0}

        with open(self.bot.data_file, 'w', encoding='utf-8') as f:
            json.dump(guilds_dict, f, ensure_ascii=False, indent=4)
            
    def add_loss(self, guild_id, member_id):
        with open(self.bot.data_file, 'r') as f:
            guilds_dict = json.load(f)
            if member_id in guilds_dict[guild_id]['hangman_data']:
                if 'losses' in guilds_dict[guild_id]['hangman_data'][member_id]:
                    guilds_dict[guild_id]['hangman_data'][member_id]['losses'] += 1
                else:
                    guilds_dict[guild_id]['hangman_data'][member_id]['losses'] = 1
            else:
                guilds_dict[guild_id]['hangman_data'][member_id] = {'wins' : 0, 'losses' : 1}
                
        with open(self.bot.data_file, 'w', encoding='utf-8') as f:
            json.dump(guilds_dict, f, ensure_ascii=False, indent=4)

async def setup(bot):
    await bot.add_cog(Hangman(bot))
    print(f'Hangman Cog is being loaded')

def teardown(bot):
    print(f'Hangman Cog is being removed')
