import discord
from discord.ext import commands, tasks
import time
import os
import json
import random

DEFAULT_PLAYER_DATA = {"round_done" : False, "round_points" : 0, "green_indices" : [], "cur_string" : "", "num_guesses" : 0, "letter_effects" : [-2]*26, "can_guess" : False}

letters = list(map(chr, range(97, 123)))
upper_letters = list(map(chr, range(65, 91)))

green =         ':green_square:'
black =         ':black_large_square:'
yellow =        ':yellow_square:'
letter_prefix = ':regional_indicator_'

class Mordle(commands.Cog):
    """
    Play Wordle against another player
    """
    def __init__(self, bot):
        self.bot = bot
        self.guild_games = {}
        self.words = []
        self.text_path = self.bot.wordle_text_path

        self.accept_timeout_length = 60
        self.game_timeout_length = 300
        self.max_guesses = 6
        self.guess_scores = [32, 16, 8, 4, 2, 1]
        self.num_rounds = 3

        self.read_words()
        self.game_loop.start()

    def read_words(self):
        with open(self.text_path, 'r') as f:
            word_list = f.readlines()
            self.words = [w.strip() for w in word_list]

    @commands.command(aliases=["mhelp"], help="Display rules for Mordle", usage="&mordlehelp")
    @commands.guild_only()
    async def mordlehelp(self, ctx, *args):
        RULES_STRING = """1. Mordle is a 1v1 game based on Wordle
        2. Both players are given the same 5 letter word to guess in 6 attempts
        3. When a player guesses a word, three different effects can be applied to each letter:
        __Black__: the guessed letter does not appear in the correct word
        __Yellow__: the guessed letter appears in the correct word but is located in a different position
        __Green__: the guessed letter appears in the correct word and is located in the same position as in the guessed word
        4. Once both players either guess the word or run out of attempts, the round ends, and the next round begins.
        5. The game ends after 3 rounds with the player with the most total points declared the winner!
        """
        SCORING_STRING = """1. Scores are based on which guess a player first unlocks a correct (green) letter as well as which guess the player gets the correct word
        2. Every green letter discovered gives the player the amount of points corresponding to that guess number
        3. When a player guesses the correct word, they receive twice the amount of points corresponding to that guess number
        4. The amount of points corresponding to each guess number is as follows:
        __First guess:__    **32 points**
        __Second guess:__   **16 points**
        __Third guess:__     **8 points**
        __Fourth guess:__    **4 points**
        __Fifth guess:__     **2 points**
        __Sixth guess:__     **1 point**
        Note: each position in the word can earn points only one time. For example, if both the first and second guesses contain a green letter in the second position, the player only receives 32 points, not 32 + 16 points.
        """
        help_embed = discord.Embed(title="Mordle Guide")
        help_embed.add_field(name="RULES", value=RULES_STRING, inline=False)
        help_embed.add_field(name="SCORING", value=SCORING_STRING, inline=False)
        await ctx.send(embed=help_embed)

    @commands.command(aliases=["mstart"], help="Start a Mordle game against another player", usage="&mordlestart <@other_player>")
    @commands.guild_only()
    async def mordlestart(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel

        # MULTIPLAYER CHECKS
        if guild.id in self.guild_games:
            await ctx.send(f"A Mordle Match has already been started in **{guild.name}**")
            return
        if len(args) != 1:
            await ctx.send("You must challenge another member of the server!")
            return
        member_ids = []
        for m in guild.members:
            member_ids.append(m.id)
        target_id = int(args[0].replace("<@","").replace(">",""))
        target_member = None
        if target_id in member_ids:
            target_member = guild.get_member(target_id)
        if target_member == None:
            return
        for g in self.guild_games:
            if self.guild_games[g]["p1data"]["id"] == member.id or self.guild_games[g]["p2data"]["id"] == member.id:
                await ctx.send(f"You are already playing a Mordle Match in another server!")
                return
            if self.guild_games[g]["p1data"]["id"] == target_id or self.guild_games[g]["p2data"]["id"] == target_id:
                await ctx.send(f"{target_member.display_name} is already playing a Mordle Match in another server!")
                return
        if target_member == member:
            await ctx.send(f"You cannot challenge yourself to a Mordle Match!")
            return
        if target_member.bot:
            await ctx.send(f"You cannot challenge a Bot to a Mordle Match!")
            return

        word = random.choice(self.words).lower()
        await ctx.send(f"**{member.mention}** has challenged {target_member.mention}. Send 'a' to accept or 'd' to decline!")
        self.guild_games[guild.id] = {"channel_id" : channel.id, "cur_round" : 0, "cur_word" : word, "started" : False, "accept_time_remaining" : self.accept_timeout_length, "game_time_remaining" : self.game_timeout_length}
        self.guild_games[guild.id]["p1data"] = {"id" : member.id, "total_points" : 0}
        self.guild_games[guild.id]["p2data"] = {"id" : target_id, "total_points" : 0}
        self.reset_player_data(guild.id)
        self.guild_games[guild.id]["p1data"]["can_guess"] = True
        self.guild_games[guild.id]["p2data"]["can_guess"] = True

    def reset_player_data(self, guild_id):
        self.guild_games[guild_id]["p1data"].update(DEFAULT_PLAYER_DATA)
        self.guild_games[guild_id]["p2data"].update(DEFAULT_PLAYER_DATA)
        
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        msg = message.content.lower()
        channel = message.channel
        member = message.author

        if isinstance(channel, discord.channel.DMChannel):
            guild_dict = None
            player_dict = None
            opponent_dict = None
            guild_id = -1
            for g in self.guild_games:
                if self.guild_games[g]["p1data"]["id"] == member.id :
                    guild_dict = self.guild_games[g]
                    player_dict = self.guild_games[g]["p1data"]
                    opponent_dict = self.guild_games[g]["p2data"]
                    guild_id = g
                    break
                elif self.guild_games[g]["p2data"]["id"] == member.id:
                    guild_dict = self.guild_games[g]
                    player_dict = self.guild_games[g]["p2data"]
                    opponent_dict = self.guild_games[g]["p1data"]
                    guild_id = g
                    break
            if guild_dict == None or player_dict == None or opponent_dict == None:
                return

            guild_dict["game_time_remaining"] = self.game_timeout_length

            if len(msg) != 5:
                return
            if not msg.isalpha():
                return
            if player_dict["can_guess"] == False:
                return
            if msg not in self.words:
                return

            player_dict["can_guess"] = False
            out_str = player_dict["cur_string"]

            guessed_letters = list(msg)
            real_letters = list(guild_dict["cur_word"])
            green_indices = list(player_dict["green_indices"])
            num_orig_greens = len(green_indices)
            spots = [-1] * 5
            spot_fills = [-1] * 5

            for i in range(len(guessed_letters)):
                if guessed_letters[i] == real_letters[i]:
                    spot_fills[i] = 1
                    spots[i] = 1
                    if i not in green_indices:
                        green_indices.append(i)
                else:
                    spot_fills[i] = -1
            player_dict["green_indices"] = list(green_indices)
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
            
            letter_effects = list(player_dict["letter_effects"])

            for i in range(len(guessed_letters)):
                for l in range(len(letters)):
                    if guessed_letters[i] != letters[l]:
                        continue
                    if letter_effects[l] == -2:
                        if spot_fills[i] == 1:
                            letter_effects[l] = 1
                        elif spot_fills[i] == 0:
                            letter_effects[l] = 0
                        elif spot_fills[i] == -1:
                            letter_effects[l] = -1
                    elif letter_effects[l] == 0:
                        if spot_fills[i] == 1:
                            letter_effects[l] = 1

            for l in range(len(letters)):
                if letter_effects[l] == -2:
                    letter_string += f"{upper_letters[l]} "
                if letter_effects[l] == -1:
                    letter_string += f"||{upper_letters[l]}|| "
                if letter_effects[l] == 0:
                    letter_string += f"__{upper_letters[l]}__ "
                if letter_effects[l] == 1:
                    letter_string += f"**{upper_letters[l]}** "

            player_dict["letter_effects"] = list(letter_effects)

            cur_guess = player_dict["num_guesses"]
            earned_points = (len(green_indices) - num_orig_greens) * self.guess_scores[cur_guess]
            player_dict["round_points"] += earned_points
            player_dict["total_points"] += earned_points

            final_string = f"{out_str}{letter_string}\n\n"

            final_string += f"+{earned_points} Points for Correct Letters\n"

            if msg == guild_dict["cur_word"]:
                correct_guess_points = self.guess_scores[cur_guess] * 2
                final_string += f"+{correct_guess_points} Points for Correct Guess\n"
                player_dict["round_points"] += correct_guess_points
                player_dict["total_points"] += correct_guess_points
                player_dict["round_done"] = True
            elif player_dict["num_guesses"] >= self.max_guesses - 1:
                final_string += f"You ran out of guesses!!! The correct word was **{guild_dict['cur_word']}**\n"
                player_dict["round_done"] = True

            final_string += f"Current Round Points: {player_dict['round_points']}\nTotal Points: {player_dict['total_points']}"

            out_embed = discord.Embed(title=f"Mordle Match Guesses", description=final_string)

            await channel.send(embed=out_embed)

            player_dict["cur_string"] = out_str
            player_dict["num_guesses"] += 1
            
            if player_dict["round_done"] == True and opponent_dict["round_done"] == True:
                player_dict["can_guess"] = False
                opponent_dict["can_guess"] = False
                p1 = await self.bot.fetch_user(str(player_dict["id"]))
                p2 = await self.bot.fetch_user(str(opponent_dict["id"]))

                await p1.send(f"**__Finished Round {guild_dict['cur_round'] + 1}!__**")
                p1_embed_desc = f"{opponent_dict['cur_string']}\nCurrent Round Points: {opponent_dict['round_points']}\n\nTotal Points: {opponent_dict['total_points']}"
                p1_embed = discord.Embed(title=f"{p2.name}'s Round {guild_dict['cur_round'] + 1} Guesses!", description=p1_embed_desc)
                await p1.send(embed=p1_embed)

                await p2.send(f"**__Finished Round {guild_dict['cur_round'] + 1}!__**")
                p2_embed_desc = f"{player_dict['cur_string']}\nCurrent Round Points: {player_dict['round_points']}\n\nTotal Points: {player_dict['total_points']}"
                p2_embed = discord.Embed(title=f"{p1.name}'s Round {guild_dict['cur_round'] + 1} Guesses!", description=p2_embed_desc)
                await p2.send(embed=p2_embed)

                guild_channel = self.bot.get_channel(guild_dict["channel_id"])
                await guild_channel.send(f"**__Finished Round {guild_dict['cur_round'] + 1}!__**")
                await guild_channel.send(embed=p1_embed)
                await guild_channel.send(embed=p2_embed)

                self.reset_player_data(guild_id)

                guild_dict["cur_round"] += 1

                if guild_dict["cur_round"] >= self.num_rounds:
                    p1_points = player_dict["total_points"]
                    p2_points = opponent_dict["total_points"]
                    if p1_points > p2_points:
                        await p1.send(f"**__The game is over. You beat {p2.name} {p1_points} - {p2_points}__**!")
                        await p2.send(f"**__The game is over. You lost to {p1.name} {p2_points} - {p1_points}__**!")
                        await guild_channel.send(f"**__The game is over. {p1.name} beat {p2.name} {p1_points} - {p2_points}__**!")
                    elif p2_points > p1_points:
                        await p1.send(f"**__The game is over. You lsot to {p2.name} {p1_points} - {p2_points}__**!")
                        await p2.send(f"**__The game is over. You beat {p1.name} {p2_points} - {p1_points}__**!")
                        await guild_channel.send(f"**__The game is over. {p2.name} beat {p1.name} {p2_points} - {p1_points}__**!")
                    else:
                        await p1.send(f"**__The game is over. You tied with {p2.name} {p1_points} - {p2_points}__**!")
                        await p2.send(f"**__The game is over. You tied with {p1.name} {p1_points} - {p2_points}__**!")
                        await guild_channel.send(f"**__The game is over. {p1.name} tied with {p2.name} {p1_points} - {p2_points}__**!")
                    del self.guild_games[guild_id]
                    return

                word = random.choice(self.words).lower()
                guild_dict["cur_word"] = word
                await p1.send(f"**__Starting Round {guild_dict['cur_round'] + 1}!__**\nBegin guessing!")
                await p2.send(f"**__Starting Round {guild_dict['cur_round'] + 1}!__**\nBegin guessing!")
                await guild_channel.send(f"**__Starting Round {guild_dict['cur_round'] + 1}__**")

                player_dict["can_guess"] = True
                opponent_dict["can_guess"] = True

            player_dict["can_guess"] = True

        elif isinstance(channel, discord.channel.TextChannel):
            guild = message.guild

            if guild.id not in self.guild_games:
                return
            guild_dict = self.guild_games[guild.id]

            if guild_dict["started"] == False:
                if member.id != guild_dict["p2data"]["id"]:
                    return
                if msg == "a" or msg == "A":
                    await channel.send(f"{member.display_name} has accepted the match!")
                    await channel.send(f"**__Starting Round {1}__**")
                    guild_dict["started"] = True
                    await self.start_match(guild.id)
                elif msg == "d" or msg == "D":
                    await channel.send(f"{member.display_name} has declined the match!")
                    del self.guild_games[guild.id]

    async def start_match(self, guild_id):
        if guild_id not in self.guild_games:
            return
        
        guild_dict = self.guild_games[guild_id]

        p1 = await self.bot.fetch_user(str(guild_dict["p1data"]["id"]))
        p2 = await self.bot.fetch_user(str(guild_dict["p2data"]["id"]))

        await p1.send(f"**Starting Mordle match against {p2.name}**\n**__Starting Round 1__**")
        await p2.send(f"**Starting Mordle match against {p1.name}**\n**__Starting Round 1__**")

    @tasks.loop(seconds=1.0)
    async def game_loop(self):
        if len(self.guild_games) > 0:
            end_list = []
            unaccept_list = []
            for g in self.guild_games:
                if self.guild_games[g]["started"] == False:
                    self.guild_games[g]["accept_time_remaining"] -= 1
                    if self.guild_games[g]["accept_time_remaining"] <= 0:
                        unaccept_list.append(g)
                    continue
                self.guild_games[g]["game_time_remaining"] -= 1
                if self.guild_games[g]["game_time_remaining"] <= 0:
                    end_list.append(g)
            for e in end_list:
                channel = self.bot.get_channel(self.guild_games[e]["channel_id"])
                p1 = await self.bot.fetch_user(str(self.guild_games[e]['p1data']["id"]))
                p2 = await self.bot.fetch_user(str(self.guild_games[e]['p2data']["id"]))
                p1_score = self.guild_games[e]['p1data']['total_points']
                p2_score = self.guild_games[e]['p2data']['total_points']
                await channel.send(f"{self.game_timeout_length} seconds passed without either player making a guess. Ending game...")
                await p1.send(f"{self.game_timeout_length} seconds passed without either player making a guess. Ending game...\nThe score was **__{p1.name}: {p1_score}__** - **__{p2.name}: {p2_score}__**")
                await p2.send(f"{self.game_timeout_length} seconds passed without either player making a guess. Ending game...\nThe score was **__{p1.name}: {p1_score}__** - **__{p2.name}: {p2_score}__**")
                await channel.send(f"The score was **__{p1.name}: {p1_score}__** - **__{p2.name}: {p2_score}__**")
                del self.guild_games[e]
            for u in unaccept_list:
                channel = self.bot.get_channel(self.guild_games[u]["channel_id"])
                p = self.guild_games[u]["p2data"]["id"]
                p_name = self.bot.get_guild(u).get_member(p).display_name
                await channel.send(f"{p_name} did not accept in time. Ending match...")
                del self.guild_games[u]

async def setup(bot):
    await bot.add_cog(Mordle(bot))
    print(f'Mordle Cog is being loaded')

def teardown(bot):
    print(f'Mordle Cog is being removed')
