class ThreeLetterGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
async def setup(bot):
    await bot.add_cog(ThreeLetterGame(bot))
    print(f'ThreeLetterGame Cog is being loaded')

def teardown(bot):
    print(f'ThreeLetterGame Cog is being removed')