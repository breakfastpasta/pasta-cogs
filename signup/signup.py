from redbot.core import commands

class SignUp(commands.Cog):
    """This is a cog for signing teams up in a custom game lobby"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def signup(self, ctx):
        """This does stuff!"""
        # Your code will go here
        await ctx.send("signup command response")
