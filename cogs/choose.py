import discord
from discord.ext import commands
import json
import os
import random

class Choose(commands.Cog):
    """
    Create a category and select a random choice from it
    """
    def __init__(self, bot):
        self.bot = bot
        self.guild_choices = {}
        self.choices_file = self.bot.choices_data_path
        self.initiate_guild_choices()

    def initiate_guild_choices(self):
        if not os.path.isfile(self.choices_file):
            self.guild_choices = {}
            for guild in self.bot.guilds:
                self.guild_choices[guild.id] = {}
            with open(self.choices_file, 'w', encoding='utf-8') as f:
                json.dump(self.guild_choices, f, ensure_ascii=False, indent=4)
        else:
            with open(self.choices_file, 'r') as f:
                self.guild_choices = json.load(f)
            for guild in self.bot.guilds:
                if str(guild.id) not in self.guild_choices:
                    self.guild_choices[guild.id] = {}
            with open(self.choices_file, 'w', encoding='utf-8') as f:
                json.dump(self.guild_choices, f, ensure_ascii=False, indent=4)

    @commands.command(help="Choose a random choice from a specified category", usage="&choose <category>")
    @commands.guild_only()
    async def choose(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        guild_dict = self.guild_choices[str(guild.id)]

        if len(args) != 1:
            await ctx.send(f"You must specify a single category to randomly choose from")
            return
        category = args[0].lower()
        if category not in guild_dict:
            await ctx.send(f"{args[0]} is not a choice category in this server!")
            return
        category_choices = list(guild_dict[category]["choices"].keys())
        if len(category_choices) < 1:
            await ctx.send(f"There are currently no options to choose from in this category")
        else:
            random_choice = random.choice(category_choices)
            await ctx.send(f"Selected __**{random_choice}**__ from *{category}*")

    @commands.command(help="Create a new choice category", usage="&createcategory <category_name>")
    @commands.guild_only()
    async def createcategory(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        guild_dict = self.guild_choices[str(guild.id)]

        if len(args) != 1:
            await ctx.send(f"You must specify a single category name to create")
            return
        category = args[0].lower()
        if category in guild_dict:
            await ctx.send(f"*{args[0]}* is already a choice category in this server!")
            return
        guild_dict[category] = {"creator": f"{member.name}#{member.discriminator}", "choices": {}}
        await ctx.send(f"Created new choice category: **{category}**")

        self.save_dict()

    @commands.command(help="Delete a specified category", usage="&deletecategory <category_name>")
    @commands.guild_only()
    async def deletecategory(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        guild_dict = self.guild_choices[str(guild.id)]

        if len(args) != 1:
            await ctx.send(f"You must specify a single category name to create")
            return
        category = args[0].lower()
        if category not in guild_dict:
            await ctx.send(f"*{args[0]}* is not a choice category in this server!")
            return
        del guild_dict[category]
        await ctx.send(f"Deleted **{category}**")

        self.save_dict()

    @commands.command(help="Add one or more choices to a specified category", usage="&addchoice <category_name> <choice1> <choice2> ...")
    @commands.guild_only()
    async def addchoice(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        guild_dict = self.guild_choices[str(guild.id)]

        if len(args) < 2:
            await ctx.send(f"You must specify the category to add choices to plus 1 or more choices to add to the category...")
            return
        category = args[0].lower()
        if category not in guild_dict:
            await ctx.send(f"Could not add choices because the category *{category}* does not exist")
            return
        category_choices = guild_dict[category]["choices"]
        choice_args = [a.lower() for a in args[1:]]
        already_exists = []
        added_successfully = []
        too_long_args = []
        for new_choice in choice_args:
            if new_choice in category_choices:
                already_exists.append(new_choice)
                continue
            elif len(new_choice) > 20:
                too_long_args.append(new_choice)
                continue
            category_choices[new_choice] = {"adder": f"{member.name}#{member.discriminator}"}
            added_successfully.append(new_choice)
                   
        success_list_string = ", ".join(added_successfully)
        fail_list_string = ", ".join(already_exists)
        if len(added_successfully) > 0:
            await ctx.send(f"Added the following choices to {category} successfully: {success_list_string}")
        if len(already_exists) > 0:
            await ctx.send(f"Could not add the following choices to {category} because they already exist: {fail_list_string}")
        if len(too_long_args) > 0:
            await ctx.send(f"Could not add some choices because they exceed the 20 character limit")

        self.save_dict()

    @commands.command(help="Remove one or more choices from a specified category", usage="&removechoice <category_name> <choice1> <choice2> ...")
    @commands.guild_only()
    async def removechoice(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        guild_dict = self.guild_choices[str(guild.id)]

        if len(args) < 2:
            await ctx.send(f"You must specify the category to add choices to plus 1 or more choices to remove from the category...")
            return
        category = args[0].lower()
        if category not in guild_dict:
            await ctx.send(f"Could not remove choices because the category *{category}* does not exist")
            return
        category_choices = guild_dict[category]["choices"]
        choice_args = [a.lower() for a in args[1:]]
        do_not_exist = []
        removed_successfully = []
        too_long_args = []
        for remove_choice in choice_args:
            if remove_choice not in category_choices:
                do_not_exist.append(remove_choice)
                continue
            elif len(remove_choice) > 20:
                too_long_args.append(remove_choice)
                continue
            del category_choices[remove_choice]
            removed_successfully.append(remove_choice)
                   
        success_list_string = ", ".join(removed_successfully)
        fail_list_string = ", ".join(do_not_exist)
        if len(removed_successfully) > 0:
            await ctx.send(f"Removed the following choices from {category} successfully: {success_list_string}")
        if len(do_not_exist) > 0:
            await ctx.send(f"Could not remove the following choices from {category} because they don't exist: {fail_list_string}")
        if len(too_long_args) > 0:
            await ctx.send(f"Could not remove some choices because they exceed the 20 character limit")

        self.save_dict()

    @commands.command(help="List all choices for all categories or all choices for a specified category", usage="[&listchoices] or [&listchoices <category_name]")
    @commands.guild_only()
    async def listchoices(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        guild_dict = self.guild_choices[str(guild.id)]

        # List all choices for all categories
        if len(args) == 0:
            with open(self.choices_file, 'r') as f:
                guilds_dict = json.load(f)
                data = guilds_dict[str(guild.id)]
                if len(data) < 1:
                    await ctx.send("There are not choice categories in this server!")
                    return
                for category in data:
                    category_dict = data[category]
                    creator = category_dict["creator"]
                    category_embed = discord.Embed(title=f"Category: {category.upper()}", description=f"created by {creator}")
                    choices = category_dict["choices"]
                    if len(choices) < 1:
                        category_embed.set_footer(text="There are currently no choices in this category")
                    else:
                        for choice in choices:
                            adder = choices[choice]["adder"]
                            category_embed.add_field(name=choice, value=f"{adder}", inline=True)
                    await ctx.send(embed=category_embed)

        # List all choices for specified category
        elif len(args) == 1:
            with open(self.choices_file, 'r') as f:
                guilds_dict = json.load(f)
                data = guilds_dict[str(guild.id)]
                category = args[0].lower()
                if category not in data:
                    await ctx.send(f"*{category}* is not a choice category in this server!")
                    return
                else:
                    category_dict = guild_dict[category]
                    creator = category_dict["creator"]
                    category_embed = discord.Embed(title=f"Category: {category.upper()}", description=f"created by {creator}")
                    choices = category_dict["choices"]
                    if len(choices) < 1:
                        category_embed.set_footer(text="There are currently no choices in this category")
                    else:
                        for choice in choices:
                            adder = choices[choice]["adder"]
                            category_embed.add_field(name=choice, value=f"{adder}", inline=True)
                    await ctx.send(embed=category_embed)
        # Error
        else:
            await ctx.send(f"You must either:\n1. Specify for which single category to list choices\nor\n2. Pass in no arguments to list all choices for all categories")

    def save_dict(self):
        with open(self.choices_file, 'w', encoding='utf-8') as f:
            json.dump(self.guild_choices, f, ensure_ascii=False, indent=4)       


async def setup(bot):
    await bot.add_cog(Choose(bot))
    print(f'Choose Cog is being loaded')

def teardown(bot):
    print(f'Choose Cog is being removed')
