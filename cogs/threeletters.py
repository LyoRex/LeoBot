import discord
from discord.ext import commands, tasks
from typing import List
import random

class ThreeLetter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_games = {}

        self.words_path = self.bot.wordfinder_text_path

        self.word_list = []

        self.game_timeout_length = 10
        self.empty_rounds_limit = 3
        self.game_loop.start()

    @commands.command(aliases=['tlstart'])
    @commands.guild_only()
    async def threeletterstart(self, ctx, timer=None):
        if timer is None:
            timer = self.game_timeout_length
        else:
            if not timer.isdigit():
                return
            timer = int(timer)
        guild = ctx.guild
        channel = ctx.channel
        member = ctx.author
        if member.bot:
            return
        if guild.id in self.guild_games:
            await ctx.send(f"A Three Letter Guess game has already been started in {guild.name}")
            return
        if channel.type != discord.ChannelType.text and channel.type != discord.ChannelType.public_thread:
            return

        chosen_word = self.choose_word()
        letters = self.get_three_random_letters(chosen_word)

        await ctx.send(f"Starting a Three Letter Guess game in {guild.name}. You have {timer} seconds to find a word that contains the following 3 letters: ")
        await ctx.send(f"**{letters}**")
        
        self.guild_games[guild.id] = {'empty_rounds_remaining': self.empty_rounds_limit,'game_time_remaining' : timer, 'max_game_time': timer, 'channel_id' : channel.id, 'players' : {}, 'next_guess_num': 0, 'cur_word' : chosen_word, 'cur_letters' : letters, 'guessed_word' : False}
        self.guild_games[guild.id]['players'][member.id] = {'guess': '', 'guess_num': -1, 'score': 0}

    @commands.command(aliases=['tlhelp'])
    @commands.guild_only()
    async def threeletterhelp(self, ctx):
        member = ctx.author

        if member.bot:
            return

        help_message = """To start a game, run '&threeletterstart'.
                            When you start a game, I will give you three random letters.
                            Your job is to find a word **with four or more letters** that contains the given three letters in order (but not necessarily consecutively).
                            You may not use the same answer as another player.
                            Valid answers will be marked with a '✅'.

                            Scores are based on the length of the word you find. Shorter word -> more points (ties are broken based on who answered first)
                            **1st place: +5 points**
                            **2nd place: +3 points**
                            **3rd place: +1 point**
                            
                            To end a game, run '&threeletterend'.
                            """

        embed = discord.Embed(title="Three Letters Rules", description=help_message)
        await ctx.send(embed=embed)

    @commands.command(aliases=['tlend'])
    @commands.guild_only()
    async def threeletterend(self, ctx):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        if guild.id not in self.guild_games:
            await ctx.send("No Three Letters games are ongoing in this server!")
            return
        if channel.id != self.guild_games[guild.id]['channel_id']:
            await ctx.send("The Three Letters game in this server is in another channel!")
            return
        if member.id not in self.guild_games[guild.id]['players']:
            await ctx.send("You must be playing the game to end it!")
            return
        
        await channel.send("Finishing Three Letters Game...")
        score_message = ""
        for p in self.guild_games[guild.id]['players']:
            score_message += f"{guild.get_member(p)}: {self.guild_games[guild.id]['players'][p]['score']}\n"
        embed = discord.Embed(title="Final Scores", description=score_message)
        await channel.send(embed=embed)
        del self.guild_games[guild.id]

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        channel = message.channel
        if channel.type != discord.ChannelType.text and channel.type != discord.ChannelType.public_thread:
            return
        msg = message.content.lower()
        if len(msg) > 20 or " " in msg:
            return
        guild = message.guild

        if guild.id not in self.guild_games:
            return
        if self.guild_games[guild.id]['channel_id'] != channel.id:
            return
        self.guild_games[guild.id]['guessed_word'] = True
        self.guild_games[guild.id]['empty_rounds_remaining'] = self.empty_rounds_limit

        # If player guesses for first time, add default guess and score value to their dictionary
        if not message.author.id in self.guild_games[guild.id]['players']:
            self.guild_games[guild.id]['players'][message.author.id] = {'guess': '', 'guess_num': -1, 'score': 0}
        if not self.letters_in_word(msg, self.guild_games[guild.id]['cur_letters']):
            return
        if not self.word_in_list(msg):
            return

        for p in self.guild_games[guild.id]['players']:
            if msg == self.guild_games[guild.id]['players'][p]['guess']:
                return

        if self.guild_games[guild.id]['players'][message.author.id]['guess'] != '':
            return

        next_guess_num = self.guild_games[guild.id]['next_guess_num']
        self.guild_games[guild.id]['players'][message.author.id]['guess'] = msg
        self.guild_games[guild.id]['players'][message.author.id]['guess_num'] = next_guess_num
        self.guild_games[guild.id]['next_guess_num'] += 1
        await message.add_reaction('✅')

    @tasks.loop(seconds=1.0)
    async def game_loop(self):
        if len(self.guild_games) < 1:
            return
        remove_list = []
        for g in self.guild_games:
            self.guild_games[g]['game_time_remaining'] -= 1
            if self.guild_games[g]['game_time_remaining'] <= 0:
                channel = self.bot.get_channel(self.guild_games[g]['channel_id'])
                # Add guilds that timed out without any guesses into the remove guild list
                if self.guild_games[g]['guessed_word'] == False:
                    self.guild_games[g]['empty_rounds_remaining'] -= 1
                    if self.guild_games[g]['empty_rounds_remaining'] <= 0:
                        remove_list.append(g)
                    else:
                        await channel.send(f"No one guessed a correct word. I was thinking of the word **{self.guild_games[g]['cur_word']}**...\nOnto the next round!")
                        new_word = self.choose_word()
                        new_letters = self.get_three_random_letters(new_word)
                        timer = self.guild_games[g]['max_game_time']
                        await channel.send(f"You have {timer} seconds to find a word that contains the following 3 letters: ")
                        await channel.send(f"**{new_letters}**")

                        self.guild_games[g]['cur_word'] = new_word
                        self.guild_games[g]['cur_letters'] = new_letters
                        self.guild_games[g]['game_time_remaining'] = self.guild_games[g]['max_game_time']
                        self.guild_games[g]['guessed_word'] = False
                        for p in self.guild_games[g]['players']:
                            self.guild_games[g]['players'][p]['guess'] = ''
                            self.guild_games[g]['players'][p]['guess_num'] = -1
                        self.guild_games[g]['next_guess_num'] = 0
                # If someone guessed, move onto next round
                else:
                    winners = self.check_winners(self.guild_games[g]['players'])
                    if len(winners) < 1:
                        await channel.send(f"No one guessed a correct word. I was thinking of the word **{self.guild_games[g]['cur_word']}**...\nOnto the next round!")
                    else:
                        winners_message = ""
                        if len(winners) > 0:
                            winner0 = winners[0]
                            self.guild_games[g]['players'][winner0]['score'] += 5
                            winner_name = self.bot.get_user(winner0).name
                            winners_message += f"**{winner_name}** : +5 points\n"
                        if len(winners) > 1:
                            winner1 = winners[1]
                            self.guild_games[g]['players'][winner1]['score'] += 3
                            winner_name = self.bot.get_user(winner1).name
                            winners_message += f"**{winner_name}** : +3 points\n"
                        if len(winners) > 2:
                            winner2 = winners[2]
                            self.guild_games[g]['players'][winner2]['score'] += 1
                            winner_name = self.bot.get_user(winner2).name
                            winners_message += f"**{winner_name}** : +1 points\n"

                        embed = discord.Embed(title="Round Winners", description=winners_message)
                        await channel.send(embed=embed)

                        score_message = ""
                        players_sorted = sorted(self.guild_games[g]['players'], key=lambda x: (self.guild_games[g]['players'][x]['score']), reverse=True)
                        for idx, p in enumerate(players_sorted):
                            player_name = self.bot.get_user(p).name
                            score_message += f"**{idx+1}. {player_name}**: {self.guild_games[g]['players'][p]['score']}\n"

                        embed = discord.Embed(title="Round Scores", description=score_message)
                        await channel.send(embed=embed)

                    new_word = self.choose_word()
                    new_letters = self.get_three_random_letters(new_word)
                    timer = self.guild_games[g]['max_game_time']
                    await channel.send(f"You have {timer} seconds to find a word that contains the following 3 letters: ")
                    await channel.send(f"**{new_letters}**")

                    self.guild_games[g]['cur_word'] = new_word
                    self.guild_games[g]['cur_letters'] = new_letters
                    self.guild_games[g]['game_time_remaining'] = self.guild_games[g]['max_game_time']
                    self.guild_games[g]['guessed_word'] = False
                    for p in self.guild_games[g]['players']:
                        self.guild_games[g]['players'][p]['guess'] = ''
                        self.guild_games[g]['players'][p]['guess_num'] = -1
                    self.guild_games[g]['next_guess_num'] = 0
        for r in remove_list:
            channel = self.bot.get_channel(self.guild_games[r]['channel_id'])
            await channel.send(f"{self.empty_rounds_limit} rounds passed without a guess. Ending game...")
            selected_word = self.guild_games[r]['cur_word']
            await channel.send(f"A correct word was **{selected_word}**")
            score_message = ""
            for p in self.guild_games[r]['players']:
                score_message += f"{self.bot.get_guild(r).get_member(p)}: {self.guild_games[r]['players'][p]['score']}\n"
            embed = discord.Embed(title="Final Scores", description=score_message)
            await channel.send(embed=embed)
            del self.guild_games[r]

    def choose_word(self):
        words = []
        with open(self.words_path, 'r') as f:
            words = f.readlines()
            words = [word.lower().strip() for word in words if len(word.lower().strip()) > 3]
        self.word_list = words
        word = random.choice(words).lower().strip()
        return word

    def word_in_list(self, word):
        return (word in self.word_list)

    def get_three_random_letters(self, word):
        indices = list(range(0, len(word)))
        chosen_indices = random.sample(indices, k=3)
        chosen_indices.sort()

        return "".join([word[index] for index in chosen_indices])

    def letters_in_word(self, word, letters):
        letter_list = list(letters)
        found_letters = False
        len_word = len(word)
        for i in range(len_word):
            if word[i] == letter_list[0]:
                for j in range(i+1, len_word):
                    if word[j] == letter_list[1]:
                        for k in range(j+1, len_word):
                            if word[k] == letter_list[2]:
                                found_letters = True
        return found_letters

    def check_winners(self, players: dict) -> List[str]:
        player_guesses = {}
        for p in players:
            if 'guess' not in players[p] or 'guess_num' not in players[p]:
                continue
            if players[p]['guess'] == '' or players[p]['guess_num'] == -1:
                continue
            player_guesses[p] = {'guess': players[p]['guess'], 'guess_num': players[p]['guess_num']}

        winners = []
        while len(player_guesses) > 0 and len(winners) < 3:
            winner = (min(player_guesses, key=lambda d: (len(player_guesses[d]['guess']), player_guesses[d]['guess_num'])))
            winners.append(winner)
            del player_guesses[winner]

        return list(winners)

async def setup(bot):
    await bot.add_cog(ThreeLetter(bot))
    print(f'ThreeLetter Cog is being loaded')

def teardown(bot):
    print(f'ThreeLetter Cog is being removed')