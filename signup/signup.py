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
            "signups_open": False,
            "team_size": 6,
            "bracket_size": 8,
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

    @signupset.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def toggleopen(self, ctx: commands.Context):
        """Toggles whether signups are open on the server"""
        new_value = not await self.config.guild(ctx.guild).signups_open()
        await self.config.guild(ctx.guild).signups_open.set(new_value)
        await ctx.send(f"Signups open status: {new_value}")

    @signupset.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def unregister(self, ctx: commands.Context, team: str):
        """Unregister a team"""
        async with self.config.guild(ctx.guild).current_teams() as current_teams:
            if current_teams.pop(team, None):
                await ctx.send(f"Unregistered team `{team}`")
                return
            await ctx.send(f"Specified team does not exist")

    @signupset.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def showteams(self, ctx):
        """Shows all currently registered teams"""
        guild_group = self.config.guild(ctx.guild)
        msg = ""
        async with guild_group.current_teams() as current_teams:
            for team, details in current_teams.items():
                msg += f"`{team}` :\n"
                msg += f"- captain: {ctx.guild.get_member(details['captain']).mention}\n"
                msg += f"- roster: {' '.join([ctx.guild.get_member(p).mention for p in details['roster']])}\n"
        
        if msg:
            await ctx.send(msg)
        else:
            await ctx.send("No teams to show")
    
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
                msg += f"`{k}` :\n"
                try:
                    msg += ''.join(f"    `{sk}`: `{sv}`\n" for sk,sv in v.items())
                except (TypeError, AttributeError) as e:
                    msg += f"    `{v}`\n"
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
    async def bracketsize(self, ctx, new_value: str):
        """Sets the amount of initial teams in the bracket"""
        if not new_value.isdigit():
            await ctx.send("Please enter an integer value")
            return
        await self.config.guild(ctx.guild).bracket_size.set(int(new_value))
        await ctx.send("Set the max bracket size: " + new_value + "teams")

    @config.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def senderiscaptain(self, ctx, new_value: bool):
        """Sets whether the command sender will be captain, otherwise first player listed"""
        await self.config.guild(ctx.guild).sender_is_captain.set(new_value)
        await ctx.send(f"New value for sender_is_captain: {new_value}")

    @staticmethod
    def _getmember(guild, mention: str):
        id = int(mention[2:-1])

        try: 
            member = guild.get_member(id)
            if not member.bot :
                return member
        except:
            return None

    async def _player_is_registered(self, guild, user_id):
        async with self.config.guild(guild).current_teams() as current_teams:
            return user_id in sum([v["roster"] for v in current_teams.values()], [])

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.describe(team_name="Your team's name")
    @app_commands.describe(players="List of player mentions")
    async def signup(self, interaction: discord.Interaction, team_name: str, players: str):
        if not await self.config.guild(interaction.guild).signups_open():
            await interaction.response.send_message("Signups are currently closed.", ephemeral=True)
            return

        team_name = re.sub(r'[^a-zA-Z0-9@.!#$%^&_+\s]', '', team_name)
        guild_group = self.config.guild(interaction.guild)
        players = re.findall(r'<@[0-9]*>', re.sub(r'[^<>@0-9\s]', '', players.strip()))
        team_size = await self.config.guild(interaction.guild).team_size()
        player_ids = []

        async def checkinput():
            msg = ""
            if len(players) != team_size:
                msg += f"Incorrect number of players. Please enter {team_size} player mentions.\n"
            if len(players) != len(set(players)):
                msg += f"Duplicate player entries. {team_size} unique players required\n"
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
                    msg += f"{team_name} already registered. Please use a different name.\n"
            
            return msg
        
        error = await checkinput()
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        async with guild_group.current_teams() as current_teams:
            current_teams[team_name] = {"captain": interaction.user.id if await guild_group.sender_is_captain() else player_ids[0], "roster": player_ids}
            
        await interaction.response.send_message(f"Signed up `{team_name}` with players {' '.join(players)}", ephemeral=False)
