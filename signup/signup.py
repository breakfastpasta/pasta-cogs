import discord

from redbot.core import Config
from redbot.core import commands, app_commands

UNIQUE_ID = 0x66EB2670

class SignUp(commands.Cog):
    """This is a cog for signing teams up in a custom game lobby"""

    def __init__(self, bot):
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        default_guild = {
            "team_size": 6,
            "sender_is_captain": True,
            "current_teams": {},
            "roster_map": {},
            "team_points": {},
        }
        self.config.register_guild(**default_guild)

        self.bot = bot

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(autohelp=True, aliases=["signups"])
    async def signup(self, ctx: commands.Context):
        """Manage signup settings"""
        pass

    @signup.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def setteamsize(self, ctx, new_value):
        """Sets the team size for signups"""
        # Your code will go here
        if not new_value.isdigit():
            await ctx.send("Please enter an integer value")
            return
        await self.config.guild(ctx.guild).team_size.set(int(new_value))
        await ctx.send("Set the max team size: " + new_value)

    @signup.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def wipedata(self, ctx):
        self.config.guild(ctx.guild).clear() 

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.describe(team_name="Your team's name")
    @app_commands.describe(players="List of player mentions")
    async def signup(self, interaction: discord.Interaction):
        guild_group = self.config.guild(ctx.guild)
        #async with guild_group.current_teams() as current_teams:
        #    current_teams[team_name] = players
        await interaction.response.send_message(f"Signup response", ephemeral=True)
