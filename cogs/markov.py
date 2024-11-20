import discord, asyncio
from discord import app_commands
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
        self.learned_msgs_file = self.bot.markov_messages_data_path
        self.initiate_guild_chains()
        self.learned_messages = []
        self.initiate_learned_messages()

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
            with open(self.chains_file, 'r', encoding='utf-8') as f:
                print(self.chains_file)
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

    def initiate_learned_messages(self):
        if not os.path.isfile(self.learned_msgs_file):
            self.learned_messages = []
        else:
            with open(self.learned_msgs_file, 'r') as f:
                message_id_strings = f.readlines()
                self.learned_messages = [int(i) for i in message_id_strings]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.type != discord.ChannelType.text and message.channel.type != discord.ChannelType.public_thread:
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

    @commands.command(help="Use the most recent 500 messages in each text channel to add to the server's Markov chains", usage="&learnhistory <number_of_recent_messages>")
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
        await ctx.send("Learning Text Channel histories...")
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

        await ctx.send("Learning Public Thread histories...")
        for c in guild.threads:
            if c.type != discord.ChannelType.public_thread:
                continue
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

    @commands.command(hidden=True, help="Clear Markov chains in current run of bot", usage="&reinitiatemarkov")
    @commands.guild_only()
    @commands.is_owner()
    async def reinitiatemarkov(self, ctx, *args):
        member = ctx.author

        self.guild_chains = {}
        self.initiate_guild_chains()
        self.learned_messages = []

    
    @app_commands.command(name="generatemarkovtext")
    async def generatemarkovtext(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        guild_dict = self.guild_chains[str(guild.id)]

        target_member = member.id
        member_dict = guild_dict[str(target_member)]

        out_msg = ""
        word = self.choose_rand_word(member_dict[" "])
        while word != "\t":
            edit_word = []
            for token in word.split(" "):
                if token.startswith("<@") and token.endswith(">"):
                    mentioned_user = token[token.find("@")+1 : -1]
                    if not mentioned_user[0].isnumeric():
                        mentioned_user = mentioned_user[1:]
                    mentioned_user_obj = guild.get_member(int(mentioned_user))
                    if mentioned_user_obj == None:
                        edit_word.append(token)
                    else:
                        edit_word.append(mentioned_user_obj.display_name)
                else:
                    edit_word.append(word)
            edit_word = " ".join(edit_word)
            out_msg += f"{edit_word} "
            word = self.choose_rand_word(member_dict[word])
        if len(out_msg) > 0:
            await interaction.response.send_message(out_msg)
        else:
            await interaction.response.send_message("Could not generate text! Try again!")

    @commands.command(help="Generate random text using the user's Markov chain", usage="[&generatetext] or [&generatetext <all | user>]")
    @commands.guild_only()
    async def generatetext(self, ctx, *args):
        filters = [arg for arg in args if arg.startswith("-")]
        num_to_generate = [arg for arg in args if arg.startswith("#")]
        if len(num_to_generate) > 1:
            await ctx.send("You can only specify up to 1 number for the amount of texts you want to generate")
            return

        args = [arg for arg in args if arg not in filters and arg not in num_to_generate]

        filters = [arg[1:] for arg in filters]
        if len(num_to_generate) == 1:
            num_to_generate = num_to_generate[0][1:]
            if not num_to_generate.isnumeric():
                await ctx.send("The amount of texts to generate must be a number between 1 and 20")
                return
            num_to_generate = int(num_to_generate)
            if num_to_generate < 1 or num_to_generate > 20:
                await ctx.send("The amount of texts to generate must be a number between 1 and 20")
                return
        else:
            num_to_generate = 1

        member = ctx.author
        guild = ctx.guild
        guild_dict = self.guild_chains[str(guild.id)]

        target_member = member.id
        member_dict = guild_dict[str(target_member)]

        if len(args) == 1:
            if args[0].lower() == "all":
                total_chain = {}
                for chain_key in guild_dict:
                    user_chain = guild_dict[chain_key]
                    for pre_word in user_chain:
                        if pre_word not in total_chain:
                            total_chain[pre_word] = user_chain[pre_word]
                        else:
                            cur_user_pre_word_chain = user_chain[pre_word]
                            total_pre_word_chain = total_chain[pre_word]

                            for post_word in cur_user_pre_word_chain:
                                if post_word not in total_pre_word_chain:
                                    total_pre_word_chain[post_word] = cur_user_pre_word_chain[post_word]
                                else:
                                    total_pre_word_chain[post_word] += cur_user_pre_word_chain[post_word]
                member_dict = total_chain
            else:
                mention = args[0]
                if mention.startswith("<@") and mention.endswith(">"):
                    mentioned_user = mention[mention.find("@")+1 : -1].replace("!","")
                    mentioned_user_obj = guild.get_member(int(mentioned_user))
                    if mentioned_user_obj != None and mentioned_user in guild_dict:
                        member_dict = guild_dict[str(mentioned_user)]

        for _ in range(num_to_generate):
            out_msg = ""
            word = self.choose_rand_word(member_dict[" "], filters=filters)
            while word != "\t":
                edit_word = []
                for token in word.split(" "):
                    if token.startswith("<@") and token.endswith(">"):
                        mentioned_user = token[token.find("@")+1 : -1]
                        if not mentioned_user[0].isnumeric():
                            mentioned_user = mentioned_user[1:]
                        mentioned_user_obj = guild.get_member(int(mentioned_user))
                        if mentioned_user_obj == None:
                            edit_word.append(token)
                        else:
                            edit_word.append(mentioned_user_obj.display_name)
                    else:
                        edit_word.append(word)
                edit_word = " ".join(edit_word)
                out_msg += f"{edit_word} "
                word = self.choose_rand_word(member_dict[word])
            if len(out_msg) > 0:
                await ctx.send(out_msg)
            else:
                await ctx.send("Could not generate text! Try again!")

    def choose_rand_word(self, word_dict, filters=[]):
        candidate_words = []
        candidate_weights = []

        for word in word_dict.keys():
            if word in filters:
                continue
            candidate_words.append(word)
            candidate_weights.append(word_dict[word])
        return random.choices(candidate_words, weights=candidate_weights, k=1)[0]

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
        with open(self.learned_msgs_file, 'w', encoding='utf-8') as f:
            for msg in self.learned_messages:
                f.write(f"{msg}\n")

async def setup(bot):
    await bot.add_cog(Markov(bot))
    print(f'Markov Cog is being loaded')

def teardown(bot):
    print(f'Markov Cog is being removed')
