import discord
import re
import time
import random
import math
import typing
import datetime

from collections import deque

from redbot.core import Config
from redbot.core import commands, app_commands

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
        async with guild_group.session() as session, guild_group.sessions() as sessions:
            if session:
                await ctx.send(f"Session in progress. Please save current session first with `[p]signupset session save`.")
                return
            new_id = max(int(id) for id in sessions) + 1 if sessions else 1
            session['id'] = new_id
            session['bracket'] = None
            session['teams'] = {}
            session['match_queue'] = []
            session['date'] = int(time.time())

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
        guild_group = self.config.guild(ctx.guild)
        async with guild_group.session() as session, guild_group.sessions() as sessions, guild_group.teams() as teams:
            if not session:
                msg = "no session to save\n"
                await ctx.send(msg)
                return
            sessions[str(session['id'])] = {
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


    @session.command(name='show')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def showsession(self, ctx: commands.Context):
        """Shows the current session"""
        msg = ""
        async with self.config.guild(ctx.guild).session() as session:
            if session:
                msg += f"id: `{str(session['id'])}`\n"
                msg += f"date: <t:{str(session['date'])}:F>\n"
                if session['bracket']:
                    msg += f"```{Bracket().from_dict(session['bracket']).show_tree()}```"
                msg += f"`{str(session['teams'])}`\n"
                msg += f"match buffer: `{str(session['match_queue'])}`"
                await ctx.send(msg)
                return
            await ctx.send("no session to show")
    
    @session.command(name='view')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def _viewsession(self, ctx: commands.Context):
        matchups = []
        async with self.config.guild(ctx.guild).session() as session:
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

    @signupset.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def toggleopen(self, ctx: commands.Context):
        """Toggles whether signups are open on the server"""
        new_value = not await self.config.guild(ctx.guild).signups_open()
        await self.config.guild(ctx.guild).signups_open.set(new_value)
        await ctx.send(f"Signups open status: {new_value}")

    @config.command(name='clear')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def clearconfig(self, ctx):
        """Wipes the server's config to default"""
        await self.config.guild(ctx.guild).clear()
        await ctx.send("Config cleared.")

    @config.command(name='show')
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def showconfig(self, ctx):
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
    
    async def get_embed(
        self, ctx: commands.Context, selected: typing.Optional[list]
    ) -> discord.Embed:
        print(f"in get_embed: {selected=}")
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
                        field_value = "*Unconfirmed*"
                    embed.add_field(name=f"`{t1.val} vs. {t2.val}`", value=field_value, inline=True)
                bracket_codeblock = bracket.show_tree()
                embed.description = f"```{bracket_codeblock}```"
        
        
        embed.set_thumbnail(url="https://example.com/example.png")
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        return embed

    async def update_bracket(self, guild, winners):
        await self._update_bracket(guild, winners)
    
    async def _update_bracket(self, guild, winners):
        print("entered _update_bracket()")
        guild_group = self.config.guild(guild)
        print(f"{guild_group=}")
        async with guild_group.session() as session:
            print("config open")
            bracket = Bracket().from_dict(session['bracket'])
            print(f"{bracket=}")
            matchups = bracket.get_matchups()
            print(f"{matchups=}")
            print(f"looping through matchups")
            for t1, t2 in matchups:
                print(f"loop run")
                if t1.val in winners:
                    print(f"t1.val in winners {t1.val=}")
                    t1.parent.val = t1.val
                    print(f"t1.val propogated {t1.val=}")
                if t2.val in winners:
                    print(f"t2.val in winners {t2.val=}")
                    t2.parent.val = t2.val
                    print(f"t1.val propogated {t1.val=}")
            print('saving session bracket...')
            session['bracket'] = dict(bracket)
            print('clearing match_queue')
            session['match_queue'].clear()
            print('queueing the next matches')
            await self._queue_matches(guild)
            print('done')
                
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
    
    async def _queue_matches(self, guild):
        async with self.config.guild(guild).session() as session:
            bracket = Bracket().from_dict(session['bracket'])
            matches = bracket.get_matchups()
            session['match_queue'].extend([[t1.val, t2.val] for t1, t2 in matches])
            return matches

    async def get_matchups(self, guild):
        return await self._get_matchups(guild)
    
    async def _get_matchups(self, guild):
        print('entered _get_matchups()')
        async with self.config.guild(guild).session() as session:
            print('in async')
            matchups = Bracket().from_dict(session['bracket']).get_matchups()
            print(f'got the matchups from bracket: {matchups=}')
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
            bracket = Bracket().from_dict(session['bracket'])
            competitors = deque(sorted(session['teams'].keys(), key=lambda x: teams[x]['points'] if x in teams else 0))
            print(f'{competitors=}')

            leaf_nodes = []
            bracket.get_leaf_nodes(leaf_nodes)
            print(f'{[l.val for l in leaf_nodes]}')
            leaf_nodes.sort(key=lambda x: bracket.get_node_depth(x), reverse=True)
            print(f'post sort {[l.val for l in leaf_nodes]}')
            
            flip = 0
            while competitors and leaf_nodes:
                node = leaf_nodes[flip]
                temp = competitors.popleft()
                prev = node.val
                node.val = temp
                print(f'popped {temp} into node w previous value {prev}')
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

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.describe(team_name="Your team's name")
    @app_commands.describe(players="List of player mentions")
    async def signup(self, interaction: discord.Interaction, team_name: str, players: str):
        guild_group = self.config.guild(interaction.guild)
        if not await guild_group.signups_open():
            await interaction.response.send_message("Signups are currently closed.", ephemeral=True)
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
