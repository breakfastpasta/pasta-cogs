import discord
import re

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

    #async def get_config(self, guild: discord.Guild):
    #    config = await self.config.guild(guild).get_raw

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(name="signupset", autohelp=True, aliases=["setsignup"])
    async def signupset(self, ctx: commands.Context):
        """Manage signup settings"""
        pass
    
    @signupset.group(name="config", autohelp=True, aliases=["conf"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def config(self, ctx: commands.Context):
        """Manage server config"""
        pass

    @config.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def reset(self, ctx):
        """Wipes the server's config to default"""
        await self.config.guild(ctx.guild).clear()
        await ctx.send("Config cleared.")

    @config.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def show(self, ctx):
        """Shows the server's current config"""
        guild_group = self.config.guild(ctx.guild)
        async with guild_group.all() as conf:
            msg = ""
            for k,v in conf.items():
                msg += (f"{k} :\n")
                try:
                    msg += "\n".join([f"    {sk}: {sv}" for sk,sv in v.items()]) + "\n"
                except (TypeError, AttributeError) as e:
                    msg += (f"    {v}\n")
        await ctx.send(msg)

    @config.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def teamsize(self, ctx, new_value: str):
        """Sets the team size for signups"""
        if not new_value.isdigit():
            await ctx.send("Please enter an integer value")
            return
        await self.config.guild(ctx.guild).team_size.set(int(new_value))
        await ctx.send("Set the max team size: " + new_value)

    @config.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def senderiscaptain(self, ctx, new_value: bool):
        """Sets whether the command sender will be captain, otherwise first player listed"""
        await self.config.guild(ctx.guild).sender_is_captain.set(new_value)
        await ctx.send(f"New value for sender_is_captain: {new_value}")

    @staticmethod
    def _getmember(guild, mention: str):
        pattern = r'<@.*[0-9]>'
        id = ""
        if re.fullmatch(pattern, mention):
            id = int(mention[2:-1])
        else:
            return None

        try: 
            member = guild.get_member(id)
            return member
        except:
            return None

    async def _player_is_registered(self, guild, user_id):
        async with self.config.guild(guild).current_teams() as current_teams:
            return user_id in sum([v for v in current_teams.values()], [])

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.describe(team_name="Your team's name")
    @app_commands.describe(players="List of player mentions")
    async def signup(self, interaction: discord.Interaction, team_name: str, players: str):
        team_name = re.sub(r'[^a-zA-Z0-9@.!#$%^&_+\s]', '', team_name)
        guild_group = self.config.guild(interaction.guild)
        players = re.sub(r'[^<>@0-9\s]', '', players.strip()).split()
        team_size = await self.config.guild(interaction.guild).team_size()
        player_ids = []

        async def checkinput():
            msg = ""
            if len(players) != team_size:
                msg += "Incorrect number of players. Please enter {team_size} player mentions.\n"
            if len(players) != len(set(players)):
                msg += "Duplicate player entries. 6 unique players required\n"
            for p in players:
                member = self._getmember(interaction.guild, p)
                if not member:
                    msg += f"{p} is not a valid member mention\n"
                    continue
                if await self._player_is_registered(interaction.guild, member.id):
                    msg += f"{p} is already registered\n"
                    continue
                player_ids.append(member.id)
            if interaction.user.id not in player_ids:
                msg += "You must be a part of the team\n"
            async with guild_group.current_teams() as current_teams:
                if team_name in current_teams:
                    msg += "Team name already registered. Please use a different name.\n"
            
            return msg
        
        error = await checkinput()
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        async with guild_group.current_teams() as current_teams:
            current_teams[team_name] = {"captain": interaction.user.id if await guild_group.sender_is_captain() else player_ids[0], "roster": player_ids}
            
        await interaction.response.send_message(f"Signed up `{team_name}` with players {players}", ephemeral=False)
