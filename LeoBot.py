import os

import asyncio
import discord
from discord.ext import commands
from discord.ext.commands import ExtensionAlreadyLoaded, ExtensionNotLoaded
import dotenv
import json
import datetime

DEFAULT_GUILD_DATA = {'name':'', 'hangman_data':{}, 'wordle_data':{}, 'baller_data': {}}

dotenv.load_dotenv()
TOKEN = os.getenv('TOKEN')
prefix = os.getenv('PREFIX')
DATA_PATH = os.getenv('DATA_PATH')
intents = discord.Intents(messages=True, guilds=True, reactions=True, members=True, presences=True)
intents.message_content = True
bot = commands.Bot(command_prefix=prefix, intents=intents)

@bot.event
@commands.is_owner()
async def on_ready():
    print('Bot is ready')
    initiate_guild_data()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands(s)")
    except Exception as e:
        print(e)
        
    await bot.change_presence(activity=discord.Game(name="Weeb Simulator"))


    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')

@bot.event
@commands.is_owner()
async def on_guild_join(guild):
    print(f"Joined {guild.name}")
    initiate_guild_data()

def initiate_guild_data():
    if not os.path.isfile(bot.data_file):
        bot.guild_data = {}
        for guild in bot.guilds:
            bot.guild_data[guild.id] = DEFAULT_GUILD_DATA
            bot.guild_data[guild.id]['name'] = guild.name
        with open(bot.data_file, 'w', encoding='utf-8') as f:
            json.dump(bot.guild_data, f, ensure_ascii=False, indent=4)
        print("Created guild JSON data file")
    else:
        print("Guild JSON data file already exists!")
        with open(bot.data_file, 'r') as f:
            bot.guild_data = json.load(f)
        for guild in bot.guilds:
            if str(guild.id) not in bot.guild_data:
                bot.guild_data[str(guild.id)] = DEFAULT_GUILD_DATA
                bot.guild_data[str(guild.id)]['name'] = guild.name
            # Add any missing keys to the guild's dictionary
            for key in DEFAULT_GUILD_DATA.keys():
                if key not in bot.guild_data[str(guild.id)].keys():
                    if type(DEFAULT_GUILD_DATA[key]) == dict:
                        bot.guild_data[str(guild.id)][key] = dict(DEFAULT_GUILD_DATA[key])
        with open(bot.data_file, 'w', encoding='utf-8') as f:
            json.dump(bot.guild_data, f, ensure_ascii=False, indent=4)

@bot.command(hidden=True)
@commands.is_owner()
async def load(ctx, module : str):
    try:
        await ctx.send(f'Loading {module}')
        await bot.load_extension(f'cogs.{module}')
        await ctx.send(f'Loaded {module}')
    except ExtensionAlreadyLoaded:
        print(f'{module} already loaded')

@bot.command(hidden=True)
@commands.is_owner()
async def unload(ctx, module : str):
    try:
        await bot.unload_extension(f'cogs.{module}')
        await ctx.send(f'Unloaded {module}')
    except ExtensionNotLoaded:
        await ctx.send(f'{module} not loaded')

@bot.command(hidden=True)
@commands.is_owner()
async def reload(ctx, module : str):
    try:
        await bot.unload_extension(f'cogs.{module}')
        await bot.load_extension(f'cogs.{module}')
        await ctx.send(f'Reloaded {module}')
    except ExtensionNotLoaded:
        await ctx.send(f'{module} not loaded')

@bot.command(hidden=True)
@commands.is_owner()
async def reloadall(ctx):
    for filename in os.listdir('./cogs'):
        try:
            if filename.endswith('.py'):
                await bot.unload_extension(f'cogs.{filename[:-3]}')
        except ExtensionNotLoaded:
            await ctx.send(f'{filename[:-3]} not loaded')
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
            await ctx.send(f'Reloaded {filename[:-3]}')

@bot.event
@commands.is_owner()
async def on_command_error(error, ctx):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send('This command cannot be used in private messages.')
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send('Sorry. This command is disabled and cannot be used.')
    elif isinstance(error, commands.CheckFailure):
        await ctx.send('Sorry. You dont have permission to use this command.')
    elif isinstance(error, commands.MissingRequiredArgument):
        command = ctx.message.content.split()[1]
        await ctx.send("Missing an argument: " + command)
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("I don't know that command")

async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

async def main():
    print(f"->Starting bot at {datetime.datetime.now().replace(microsecond=0)}")
    data_path = DATA_PATH
    bot.pics_path = "pics"
    bot.data_file = os.path.join(data_path, "data", "guilds.json")
    bot.guild_data = {}
    bot.wordle_text_path = "word_lists/wordlewords.txt"
    bot.hangman_text_path = "word_lists/hangmanwords.txt"
    bot.wordfinder_text_path = "word_lists/bogglewords.txt"
    bot.markov_chains_data_path = os.path.join(data_path, "data", "chains.json")
    bot.markov_messages_data_path = os.path.join(data_path, "data", "learned_messages.txt")
    bot.choices_data_path = os.path.join(data_path, "data", "choices.json")
    bot.pokedex_path = os.path.join("data", "pokedex.json")

    await load_extensions()

    async with bot:
        await bot.start(TOKEN)

    print(f"->Ending bot at {datetime.datetime.now().replace(microsecond=0)}")

#if __name__ == "__main__":
asyncio.run(main())
