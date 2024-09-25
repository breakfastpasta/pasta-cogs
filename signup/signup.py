import discord
import re
import time
import random
import math
import typing
import datetime
import os
import json
import io

from collections import deque

from redbot.core import Config
from redbot.core import commands, app_commands
from redbot.core import data_manager

from .bracket import Bracket, BracketNode
from .view import TournamentView

from redbot.core.utils.chat_formatting import box

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
            "session": {},
            "teams": {},
            "default_signup_channel": None,
            "default_thread_channel": None,
            "sessions": {},
        }
        default_member = {
            "team_history": []
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

        self.bot = bot

    #async def get_config(self, guild: discord.Guild):
    #    config = await self.config.guild(guild).get_raw

    @commands.group(name="signupset", autohelp=True, aliases=["setsignup"])
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def signupset(self, ctx: commands.Context):
        """Manage signup settings"""
        pass

    @signupset.group(name="session", autohelp=True, aliases=["sessions"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def session(self, ctx: commands.Context):
        """Manage sessions"""
        pass

    @signupset.group(name="config", autohelp=True, aliases=["conf"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def config(self, ctx: commands.Context):
        """Manage server config"""
        pass

    @session.command(name='new')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def newsession(self, ctx: commands.Context):
        """Start a new session"""
        guild_group = self.config.guild(ctx.guild)
        threadchannel = await guild_group.default_thread_channel()
        async with guild_group.session() as session, guild_group.sessions() as sessions:
            if session:
                await ctx.send(f"Session in progress. Please save current session first with `[p]signupset session save`.")
                return
            new_id = max(int(id) for id in sessions) + 1 if sessions else 1
            session['id'] = new_id
            session['bracket'] = None
            session['bracket_history'] = []
            session['teams'] = {}
            session['match_queue'] = []
            session['date'] = int(time.time())
            session['threadchannel'] = threadchannel

            await ctx.send(f"New session created with id `{new_id}`.")

    @session.command(name='clear')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def clearsession(self, ctx: commands.Context):
        """Deletes the current session"""
        guild_group = self.config.guild(ctx.guild)
        async with guild_group.session() as session:
            session.clear()
            await ctx.send('session cleared')

    @session.command(name='save')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def savesession(self, ctx: commands.Context):
        """Saves the current session to history"""
        return await self._save_session(ctx.guild)

    @session.command(name='show')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def showsession(self, ctx: commands.Context, session_id=None):
        """Shows the current session"""
        embed: discord.Embed = discord.Embed(
            title="Session static overview",
            color=await ctx.embed_color()
        )
        guild_group = self.config.guild(ctx.guild)
        async with guild_group.session() as session, guild_group.sessions() as sessions:
            
            to_show = session
            if session_id and not session_id == session['id']:
                to_show = sessions[session_id]
            else:
                session_id = session['id']
                
            if to_show:
                desc = "No bracket"
                if to_show['bracket']:
                    desc = f"```{Bracket().from_dict(to_show['bracket']).show_tree()}```"
                embed.add_field(name="id", value=f"`{str(session_id)}`", inline=False)
                embed.add_field(name="date", value=f"<t:{str(to_show['date'])}:F>", inline=False)
                captain_mention=''
                for team in to_show['teams']:
                    players_readable = []
                    for player in to_show['teams'][team]['roster']:
                        guild_member = ctx.guild.get_member(player)
                        if player == to_show['teams'][team]['captain']:
                            captain_mention = guild_member.mention if guild_member else player
                        mention = guild_member.mention if guild_member else player                       
                        players_readable.append(mention)
                        
                    field_value = f"{' '.join(players_readable)}\ncaptain: {captain_mention}"
                    embed.add_field(name=to_show['teams'][team]['name'], value=field_value, inline=True)
                if 'match_queue' in to_show and to_show['match_queue']:
                    embed.add_field(name="current matchups", value="\n".join(f"{t1} vs. {t2}" for t1, t2 in session['match_queue']), inline=False)
                
                embed.description = desc
                embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
                embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
                print("getting file")
                #file_to_send = await self._get_bracket_as_file(ctx.guild)
                print("got file")
                await ctx.send(embeds=[embed])
                return
            await ctx.send("no session to show")
    
    @session.command(name='view')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def _viewsession(self, ctx: commands.Context):
        matchups = []
        async with self.config.guild(ctx.guild).session() as session:
            if not session:
                await ctx.send("no session!")
                return
            matchups = session['match_queue']
        await TournamentView(cog=self).start(ctx, matchups=matchups)


    @session.command(name='addteam', aliases=['add', 'a'])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def addteam(self, ctx: commands.Context, uid, *players, points=0, name=None):
        """adds a team to the session"""
        guild_group = self.config.guild(ctx.guild)
        async with guild_group.session() as session:
            if not session:
                return
            if uid in session['teams']:
                return
            name = uid if not name else name
            session['teams'][uid] = {
                'name' : name,
                'points': points,
                'roster': players,
                'captain': players[0] if players else '',
            }
    
    @session.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def resetbracket(self, ctx: commands.Context):
        """Deletes the current bracket"""
        async with self.config.guild(ctx.guild).session() as session:
            session['bracket'].clear()
            await ctx.send('bracket removed')

    @session.command(name='placeteams')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def placeteams(self, ctx: commands.Context):
        """Places initial matchups in the bracket"""
        await self._place_teams(ctx.guild)

    @session.command(name='queuematches')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def queuematches(self, ctx: commands.Context):
        matches = await self._queue_matches(ctx.guild)
        await ctx.send(f'placed {matches} into the queue')
    
    @session.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def genbracket(self, ctx: commands.Context):
        """generates an empty bracket"""
        await self._generate_bracket(ctx.guild)
    
    @session.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def unregister(self, ctx: commands.Context, team: str):
        """Unregister a team"""
        async with self.config.guild(ctx.guild).session() as session:
            if session['teams'].pop(team, None):
                await ctx.send(f"Unregistered team `{team}`")
                return
            await ctx.send(f"Specified team does not exist")

    @session.command(name='showteams', aliases=['teams'])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def showteams(self, ctx):
        """Shows all currently registered teams"""
        guild_group = self.config.guild(ctx.guild)
        msg = ""
        async with guild_group.session() as session:
            for team, details in session['teams'].items():
                msg += f"`{team}` :\n"
                msg += f"- captain: {ctx.guild.get_member(details['captain']).mention}\n"
                msg += f"- roster: {' '.join([ctx.guild.get_member(p).mention for p in details['roster']])}\n"
        
        if msg:
            await ctx.send(msg)
        else:
            await ctx.send("No teams to show")
    
    @session.command(name='makethreads', aliases=['createthreads'])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def makethreads(self, ctx):
        guild_group = self.config.guild(ctx.guild)
        async with guild_group.session() as session:
            channel = ctx.guild.get_channel(session['threadchannel'])
            await ctx.send(channel.mention)

            # thread = await channel.create_thread(name=thread_name, auto_archive_duration=60)

            # # Add members to the thread
            # for member_id in member_ids:
            #     member = ctx.guild.get_member(member_id)
            #     if member:
            #         await thread.add_user(member)
            #     else:
            #         await ctx.send(f"Member with ID {member_id} not found.")

            # await ctx.send(f"Thread '{thread_name}' created and members added successfully.")
            #         #get current matches
            #         #find players in those matches
            #         #add each set of players to new thread in channel
            #         pass

    @signupset.command(name='threadchannel')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def _setdefaultthreadchannel(self, ctx, channel):
        channel_mention = re.search(r'<#[0-9]*>', re.sub(r'[^<>#0-9\s]', '', channel.strip())).group()
        print(channel_mention)
        channel = self._getchannel(ctx.guild, channel_mention)
        if not channel:
            await ctx.send("invalid channel")
            return
        guild_group = self.config.guild(ctx.guild)
        await guild_group.default_thread_channel.set(channel.id)
        await ctx.send(f"set default channel as {channel_mention}")
    
    @signupset.command(name='signupchannel')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def _setdefaultsignupchannel(self, ctx, channel):
        channel_mention = re.search(r'<#[0-9]*>', re.sub(r'[^<>#0-9\s]', '', channel.strip())).group()
        print(channel_mention)
        channel = self._getchannel(ctx.guild, channel_mention)
        if not channel:
            await ctx.send("invalid channel")
            return
        guild_group = self.config.guild(ctx.guild)
        await guild_group.default_signup_channel.set(channel.id)
        await ctx.send(f"set signup channel as {channel_mention}")

    @signupset.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def toggleopen(self, ctx: commands.Context):
        """Toggles whether signups are open on the server"""
        result = await self._toggleopen(ctx.guild)
        await ctx.send(f"Signups are now: `{'Open' if result else 'Closed'}`")

    async def _toggleopen(self, guild):
        new_value = not await self.config.guild(guild).signups_open()
        await self.config.guild(guild).signups_open.set(new_value)
        return new_value

    @config.command(name='clear')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def clearconfig(self, ctx):
        """Wipes the server's config to default"""
        await self.config.guild(ctx.guild).clear()
        await ctx.send("Config cleared.")

    # @config.command(name='show')
    # @commands.guild_only()
    # @commands.admin_or_permissions(manage_guild=True)
    # async def showconfig(self, ctx):
    #     """Shows the server's current config"""
    #     guild_group = self.config.guild(ctx.guild)
    #     async with guild_group.all() as conf:
    #         msg = ""
    #         for k,v in conf.items():
    #             msg += f"`{k}` :\n"
    #             try:
    #                 msg += ''.join(f"    `{sk}`: `{sv}`\n" for sk,sv in v.items())
    #             except (TypeError, AttributeError) as e:
    #                 msg += f"    `{v}`\n"
    #     await ctx.send(msg)

    @config.command(name='get')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def getconfig(self, ctx):
        """Get the current cog config as json file"""
        path = os.path.join(data_manager.cog_data_path(self), 'settings.json')
        discord_file = discord.File(path, filename='db.json')
        await ctx.send(file=discord_file)

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
        member_id = int(mention[2:-1])

        try: 
            member = guild.get_member(member_id)
            if not member.bot :
                return member
        except:
            return None
    
    @staticmethod
    def _getchannel(guild, mention: str):
        channel_id = int(mention[2:-1])

        try:
            channel = guild.get_channel(channel_id)
            return channel
        except:
            return None
    
    async def get_embed(
        self, ctx: commands.Context, selected: typing.Optional[list]
    ) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title="Session view",
            color=await ctx.embed_color(),
        )

        bracket_codeblock = None
        async with self.config.guild(ctx.guild).session() as session:
            if session:
                bracket = Bracket().from_dict(session['bracket'])
                matchups = bracket.get_matchups()
                for t1, t2 in matchups:
                    if t1.val in selected:
                        field_value = t1.val
                    elif t2.val in selected:
                        field_value = t2.val
                    else:
                        field_value = "*Undecided*"
                    embed.add_field(name=f"`{t1.val} vs. {t2.val}`", value=field_value, inline=True)
                bracket_codeblock = bracket.show_tree()
                embed.description = f"```{bracket_codeblock}```"
        
        
        #embed.set_thumbnail(url="https://example.com/example.png")
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        return embed

    async def update_bracket(self, guild, winners):
        await self._update_bracket(guild, winners)
    
    async def save_session(self, ctx):
        return await self._save_session(ctx)

    async def _update_bracket(self, guild, winners):
        guild_group = self.config.guild(guild)
        async with guild_group.session() as session:
            bracket = Bracket().from_dict(session['bracket'])
            matchups = bracket.get_matchups()
            for t1, t2 in matchups:
                if t1.val in winners:
                    t1.parent.val = t1.val
                if t2.val in winners:
                    t2.parent.val = t2.val
            session['bracket_history'].append(session['bracket'])
            session['bracket'] = dict(bracket)
            session['match_queue'].clear()
        await self._queue_matches(guild)
    
    async def revert_bracket(self, guild):
        await self._revert_bracket(guild)
                
    async def _generate_bracket(self, guild):
        guild_group = self.config.guild(guild)
        async with guild_group.session() as session:
            team_count = len(session['teams'])
            bracket_dict = dict(Bracket().create_bracket(math.log(team_count, 2) + 1,team_count))
            session['bracket'] = bracket_dict

    async def _generate_matchups(self, guild):
        guild_group = self.config.guild(guild)
        async with guild_group.session() as session:
            pass
        return ret

    async def _player_is_registered(self, guild, user_id):
        async with self.config.guild(guild).session() as session:
            return user_id in sum([v["roster"] for v in session['teams'].values()], [])
    
    async def _save_data(self, guild):
        guild_group = self.config.guild(guild)
        async with guild_group.sessions() as sessions, guild_group.teams() as teams:
            pass
        await guild_group.session.set(None)

    async def _revert_bracket(self, guild):
        guild_group = self.config.guild(guild)
        async with guild_group.session() as session:
            history = session['bracket_history']
            if history:
                session['bracket'] = history.pop()
    
    async def _queue_matches(self, guild):
        async with self.config.guild(guild).session() as session:
            bracket = Bracket().from_dict(session['bracket'])
            matches = bracket.get_matchups()
            session['match_queue'] = [[t1.val, t2.val] for t1, t2 in matches]
            return matches

    async def _save_session(self, guild):
        guild_group = self.config.guild(guild)
        async with guild_group.session() as session, guild_group.sessions() as sessions, guild_group.teams() as teams:
            if not session:
                return "no session to save"
            session_id = session['id']
            sessions[str(session_id)] = {
                'bracket': session['bracket'],
                'teams': session['teams'],
                'date': session['date'],
            }
            for team in session['teams']:
                if team not in teams:
                    teams[team] = {
                        'players': [],
                        'points': 0,
                        'points_total': 0,
                        'captains': [],
                        'matches': 0,
                        'scrim_wins': 0,
                        'cup_wins': 0,
                    }
                captains = set(teams[team]['captains'])
                captains.add(session['teams'][team]['captain'])
                players = set(teams[team]['players']) | set(session['teams'][team]['roster'])
                teams[team]['captains'] = list(captains)
                teams[team]['players'] = list(players)
                teams[team]['points'] += session['teams'][team]['points']
                teams[team]['points_total'] += session['teams'][team]['points']
                teams[team]['matches'] += 0
                teams[team]['scrim_wins'] += 0
                teams[team]['cup_wins'] += 0
            session.clear()
            
            return f"Saved session with id `{session_id}`"


    async def get_matchups(self, guild):
        return await self._get_matchups(guild)
    
    async def _get_matchups(self, guild):
        async with self.config.guild(guild).session() as session:
            matchups = Bracket().from_dict(session['bracket']).get_matchups()
            h_matchups = []
            h_matchups.extend([[t1.val, t2.val] for t1, t2 in matchups])
            return h_matchups


    # async def _assign_teams(self, guild):
    #     guild_group = self.config.guild(guild)
    #     async with guild_group.session() as session, guild_group.teams() as teams:
    #         bracket = Bracket().from_dict(session['bracket'])
    #         seeds = sorted(session['teams'].keys(), key=lambda x: teams[x]['points'] if x in teams else 0)
    #         depth = math.log(len(session['teams']), 2)
    #         team_q = deque(seeds)
    #         seed = 1
    #         def place_teams(root):
    #             nonlocal seed
    #             if not root:
    #                 return
    #             if not (root.left or root.right):
    #                 popside = {1: team_q.popleft, 0: team_q.pop}[seed]
    #                 temp = popside()
    #                 root.val = temp
    #                 print(f"popped {temp} into root.val")
    #                 seed = not seed
    #             place_teams(root.left)
    #             place_teams(root.right)
                
    #         place_teams(bracket.root)
    #         session['bracket'] = dict(bracket)

    async def _place_teams(self, guild):
        guild_group = self.config.guild(guild)
        async with guild_group.session() as session, guild_group.teams() as teams:
            if not session['bracket']:
                return
            bracket = Bracket().from_dict(session['bracket'])
            competitors = deque(sorted(session['teams'].keys(), key=lambda x: teams[x]['points'] if x in teams else 0))

            leaf_nodes = []
            bracket.get_leaf_nodes(leaf_nodes)
            leaf_nodes.sort(key=lambda x: bracket.get_node_depth(x), reverse=True)
            
            flip = 0
            while competitors and leaf_nodes:
                node = leaf_nodes[flip]
                temp = competitors.popleft()
                prev = node.val
                node.val = temp
                leaf_nodes.remove(node)
                flip = 0 if flip else -1


                # for i in range(0, len(leaf_nodes), 2):
                #     if competitors:
                #         temp = competitors.popleft()
                #         leaf_nodes[i].val = temp
                #         print(f'popped {temp} into leaf {i}')
                
                # for i in range(len(leaf_nodes)-1, 0, -2):
                #     if competitors:
                #         temp = competitors.popleft()
                #         leaf_nodes[i].val = temp
                #         print(f'popped {temp} into leaf {i}')
                
                # leaf_nodes = [node for node in leaf_nodes if not node.val]
            
            session['bracket'] = dict(bracket)
        await self._queue_matches(guild)

    async def _session_is_full(self, guild):
        guild_group = self.config.guild(guild)
        max_teams = await guild_group.bracket_size()
        async with guild_group.session() as session:
            if len(session['teams']) >= max_teams:
                return True
        return False
    
    async def get_bracket_as_file(self, ctx):
        print("trying to get file")
        return await self._get_bracket_as_file(ctx.guild)
    
    async def _get_bracket_as_file(self, guild):
        print("entered function")
        guild_group = self.config.guild(guild)
        print("got guild group")
        async with guild_group.session() as session:
            print("getting bracket")
            text = Bracket().from_dict(session['bracket']).show_tree()
            print("bracket text:" + text)
            file = io.BytesIO(text.encode('utf-8'))
            print("created file")
            discord_file = discord.File(file, filename='bracket.txt')
            print("created discord file")
            file.close()

            print("returning file")
            return discord_file

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.describe(team_name="Your team's name")
    @app_commands.describe(players="List of player mentions")
    async def signup(self, interaction: discord.Interaction, team_name: str, players: str):
        guild_group = self.config.guild(interaction.guild)
        if not await guild_group.signups_open():
            await interaction.response.send_message("Signups are currently closed.", ephemeral=True)
            return
        if interaction.channel.id != await guild_group.default_signup_channel():
            await interaction.response.send_message("Wrong channel", ephemeral=True)
            return

        team_name = re.sub(r'[^a-zA-Z0-9@.!#$%^&_+\s]', '', team_name)
        players = re.findall(r'<@[0-9]*>', re.sub(r'[^<>@0-9\s]', '', players.strip()))
        team_size = await guild_group.team_size()
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
            async with guild_group.session() as session:
                if team_name in session['teams']:
                    msg += f"{team_name} already registered. Please use a different name.\n"
            
            return msg
        
        error = await checkinput()
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        async with guild_group.session() as session:
            sender_is_captain = await guild_group.sender_is_captain()
            session['teams'][team_name] = {   
                "name": team_name,
                "captain": interaction.user.id if sender_is_captain else player_ids[0], 
                "roster": player_ids,
                "points": 0,
            }
            
        await interaction.response.send_message(f"Signed up `{team_name}` with players {' '.join(players)}", ephemeral=False)

        if await self._session_is_full(interaction.guild):
            await self._toggleopen(interaction.guild)
            await interaction.followup.send("Last team registered! Signups now CLOSED")
