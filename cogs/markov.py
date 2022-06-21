import discord
from discord.ext import commands
import os
import json
import re
import random

class Markov(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_chains = {}
        self.chains_file = self.bot.markov_chains_data_path
        self.initiate_guild_chains()
        self.learned_messages = []

    def initiate_guild_chains(self):
        if not os.path.isfile(self.chains_file):
            self.guild_chains = {}
            for guild in self.bot.guilds:
                self.guild_chains[guild.id] = {}
                for member in guild.members:
                    if member.bot:
                        continue
                    self.guild_chains[guild.id][member.id] = {}
            with open(self.chains_file, 'w', encoding='utf-8') as f:
                json.dump(self.guild_chains, f, ensure_ascii=False, indent=4)
        else:
            with open(self.chains_file, 'r') as f:
                self.guild_chains = json.load(f)
            for guild in self.bot.guilds:
                if str(guild.id) not in self.guild_chains:
                    self.guild_chains[guild.id] = {}
                    for member in guild.members:
                        if member.bot:
                            continue
                        self.guild_chains[guild.id][member.id] = {}
            with open(self.chains_file, 'w', encoding='utf-8') as f:
                json.dump(self.guild_chains, f, ensure_ascii=False, indent=4)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.channel, discord.channel.TextChannel):
            return
        if message.author.bot:
            return
        parsed_message = self.parse_message(message.content)
        if len(parsed_message) < 3:
            return
        if message.id in self.learned_messages:
            return
        guild = message.guild
        self.learn(str(guild.id), str(message.author.id), parsed_message)
        self.learned_messages.append(message.id)

        self.save_dict()

    @commands.command()
    @commands.guild_only()
    async def learnhistory(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel

        lim = 500

        if len(args) == 1:
            try:
                lim = int(args[0])
            except ValueError:
                pass

        await ctx.send("Learning messages histories...")

        for c in guild.text_channels:
            async for message in c.history(limit = lim):
                if message.author.bot:
                    continue
                parsed_message = self.parse_message(message.content)
                if len(parsed_message) < 3:
                    continue
                if message.id in self.learned_messages:
                    continue
                self.learn(str(guild.id), str(message.author.id), parsed_message)
                self.learned_messages.append(message.id)

        self.save_dict()
        await ctx.send("Finished learning messages!")

    @commands.command()
    @commands.guild_only()
    async def reinitiatemarkov(self, ctx, *args):
        member = ctx.author

        self.guild_chains = {}
        self.initiate_guild_chains()
        self.learned_messages = []

    @commands.command()
    @commands.guild_only()
    async def generatetext(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        guild_dict = self.guild_chains[str(guild.id)]
        
        target_member = member.id

        if len(args) == 1:
            target_id = args[0].replace('<@','').replace('>','')
            if str(target_id) in guild_dict:
                target_member = target_id

        member_dict = guild_dict[str(target_member)]

        out_msg = ""
        word = self.choose_rand_word(member_dict[" "])
        while word != "\t":
            edit_word = word
            out_msg += f"{edit_word} "
            word = self.choose_rand_word(member_dict[word])
        if len(out_msg) > 0:
            await ctx.send(out_msg)
        else:
            await ctx.send("Could not generate text! Try again!")

    def choose_rand_word(self, word_dict):
        word_list = []
        for k in word_dict:
            word_list += [k] * word_dict[k]
        return random.choice(word_list)

    def parse_message(self, msg: str):
        words = msg.split()
        ret_words = []
        for word in words:
            if "http://" in word or "https://" in word:
                continue
            ret_words.append(word)
        return ret_words

    def learn(self, guild_id, user_id, message):
        if guild_id not in self.guild_chains:
            self.guild_chains[guild_id] = {}
        if user_id not in self.guild_chains[guild_id]:
            self.guild_chains[guild_id][user_id] = {}
        user_chain = self.guild_chains[guild_id][user_id]

        words = message

        if " " not in user_chain:
            user_chain[" "] = {}
        if words[0] not in user_chain[" "]:
            user_chain[" "][words[0]] = 0
        user_chain[" "][words[0]] += 1
        cur_word = ""
        for i in range(len(words)):
            if words[i] not in user_chain:
                user_chain[words[i]] = {}
            if i < len(words) - 1:
                if words[i+1] not in user_chain[words[i]]:
                    user_chain[words[i]][words[i+1]] = 0
                user_chain[words[i]][words[i+1]] += 1
            else:
                if "\t" not in user_chain[words[i]]:
                    user_chain[words[i]]["\t"] = 0
                user_chain[words[i]]["\t"] += 1
    
    def save_dict(self):
        with open(self.chains_file, 'w', encoding='utf-8') as f:
            json.dump(self.guild_chains, f, ensure_ascii=False, indent=4)

def setup(bot):
    bot.add_cog(Markov(bot))
    print(f'Markov Cog is being loaded')

def teardown(bot):
    print(f'Markov Cog is being removed')