import discord
from discord.ext import commands

ERROR = '**Poll usage**:\n**Multiple Choices**\n&poll "Question" "Choice 1" "Choice 2" "Choice 3"....etc\n**Yes/No ' \
        'Question**\n&poll "Question" '

number_emojis = [
    '\N{Regional Indicator Symbol Letter A}',
    '\N{Regional Indicator Symbol Letter B}',
    '\N{Regional Indicator Symbol Letter C}',
    '\N{Regional Indicator Symbol Letter D}',
    '\N{Regional Indicator Symbol Letter E}',
    '\N{Regional Indicator Symbol Letter F}',
    '\N{Regional Indicator Symbol Letter G}',
    '\N{Regional Indicator Symbol Letter H}',
    '\N{Regional Indicator Symbol Letter I}',
    '\N{Regional Indicator Symbol Letter J}',
    '\N{Regional Indicator Symbol Letter K}',
    '\N{Regional Indicator Symbol Letter L}',
    '\N{Regional Indicator Symbol Letter M}',
    '\N{Regional Indicator Symbol Letter N}',
    '\N{Regional Indicator Symbol Letter O}',
    '\N{Regional Indicator Symbol Letter P}',
    '\N{Regional Indicator Symbol Letter Q}',
    '\N{Regional Indicator Symbol Letter R}',
    '\N{Regional Indicator Symbol Letter S}',
    '\N{Regional Indicator Symbol Letter T}',
    '\N{Regional Indicator Symbol Letter U}',
    '\N{Regional Indicator Symbol Letter V}',
    '\N{Regional Indicator Symbol Letter W}',
    '\N{Regional Indicator Symbol Letter X}',
    '\N{Regional Indicator Symbol Letter Y}',
    '\N{Regional Indicator Symbol Letter Z}'
]

def split_by_surround(phrase: str, delim: str):
    split = []
    delim_locs = [pos for pos, char in enumerate(phrase) if char == delim]
    if len(delim_locs) % 2 == 1:
        return []
    for i in range(0, len(delim_locs), 2):
        split.append(phrase[delim_locs[i] + 1 : delim_locs[i+1]])

    return split

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Create a poll for people to vote on", usage="[&poll <question>] or [&poll <question> <choice1> <choice2> ...]")
    @commands.guild_only()
    async def poll(self, ctx, *, input="Hello"):
        if input.lstrip()[0] != '"':
            await ctx.send(ERROR)
            return
        split_inputs = split_by_surround(str(input), '"')
        if len(split_inputs) >= 1:
            question = split_inputs[0]
            choices = split_inputs[1:]
        else:
            await ctx.send(ERROR)
            return

        output_msg = ""
        question = f'❓ **{question}** ❓\n'
        output_msg += question

        if len(choices) == 0:
            msg = await ctx.send(output_msg)
            await msg.add_reaction('\N{THUMBS UP SIGN}')
            await msg.add_reaction('\N{THUMBS DOWN SIGN}')
        else:
            output_msg += ">>> "
            for i in range(len(choices)):
                choice = f'{number_emojis[i]} {choices[i]}'
                output_msg += f' {choice}'
                if i != len(choices) - 1:
                    output_msg += "\n"
            msg = await ctx.send(output_msg)
            for i in range(len(choices)):
                await msg.add_reaction(number_emojis[i])


async def setup(bot):
    await bot.add_cog(Poll(bot))
    print(f'Poll Cog is being loaded')


def teardown(bot):
    print(f'Poll Cog is being removed')

