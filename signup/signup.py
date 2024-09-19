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
        default_member = {
            "team_history": []
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

        self.bot = bot

    async def get_config(self, guild: discord.Guild):
        config = await self.config.guild(guild).get_raw

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(name="signupset", autohelp=True, aliases=["setsignup"])
    async def signupset(self, ctx: commands.Context):
        """Manage signup settings"""
        pass

    @signupset.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def teamsize(self, ctx, new_value):
        """Sets the team size for signups"""
        if not new_value.isdigit():
            await ctx.send("Please enter an integer value")
            return
        await self.config.guild(ctx.guild).team_size.set(int(new_value))
        await ctx.send("Set the max team size: " + new_value)

    @signupset.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def wipedata(self, ctx):
        """Wipes the server's config"""
        self.config.guild(ctx.guild).clear()

    @signupset.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def showconfig(self, ctx):
        """Shows the server's current config"""
        guild_group = self.config.guild(ctx.guild)
        conf = guild_group.all()
        msg = ""
        for k,v in conf.items():
            msg.append(f"{k} :\n")
            try:
                msg.append([f"    {sk}: {sv}" for sk,sv in v.items()])
            except TypeError:
                msg.append(f"    {v}\n")
        await ctx.send(msg)

    @app_commands.command()
    @app_commands.guild_only()
    #@app_commands.describe(team_name="Your team's name")
    #@app_commands.describe(players="List of player mentions")
    async def signup(self, interaction: discord.Interaction, team_name: str):
        guild_group = self.config.guild(interaction.guild)
        #async with guild_group.current_teams() as current_teams:
        #    current_teams[team_name] = players
        await interaction.response.send_message(f"Signup response", ephemeral=True)
