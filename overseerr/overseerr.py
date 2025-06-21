import discord
import asyncio
import datetime
import re
import logging

from functools import wraps

from redbot.core import commands, app_commands
from redbot.core import Config

from .api import Overseerr_API
from .view import RequestView, SearchView

logger = logging.getLogger(__name__)

UNIQUE_ID = 0x6714473D

class Overseerr(commands.Cog):
    """Make requests to an overseerr endpoint"""

    def __init__(self, bot):
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        default_global = {
            "endpoint": None,
            "guild_whitelist": []
        }
        default_guild = {
            "download_dir" : None,
            "request_role": None,
        }
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

        self.bot = bot
    
    async def cog_load(self) -> None:
        await super().cog_load()
        endpoint = await self.config.endpoint()
        keys = await self.bot.get_shared_api_tokens("overseerr")
        api_key = None
        if keys.get("api_key"):
            api_key = keys['api_key']

        self.api = Overseerr_API(endpoint=endpoint, api_key=api_key)
    
    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service, api_tokens):
        if service == "overseerr" and api_tokens.get("api_key"):
            await self.api.set_api_key(api_tokens['api_key'])
    

    async def _is_guild_whitelisted(self, ctx):
        if guild := getattr(ctx, 'guild', None):
            r = guild.id in await self.config.guild_whitelist()
            logger.debug(r)
            logger.debug(await self.config.guild_whitelist())
            return r
            #return guild.id in await self.config.guild_whitelist()
        return False

    async def query_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        if not await self._is_guild_whitelisted(interaction):
            return []
        ret: list[app_commands.Choice[str]] = []
        current = re.sub(r'[^a-zA-Z\d\s]', '', current.strip())
        results = await self.api.search(current)
        if results:
            for r in results:
                match r['mediaType']:
                    case 'tv':
                        name = f"[TV] {r['name']} ({r['firstAirDate'].split('-')[0]})"
                        val = f"<id:{str(r['id'])}>,<type:{str(r['mediaType'])}>"
                        ret.append(app_commands.Choice(name=name, value=val))
                    case 'movie':
                        name = f"[MOVIE] {r['title']} ({r['releaseDate'].split('-')[0]})"
                        val = f"<id:{str(r['id'])}>,<type:{str(r['mediaType'])}>"
                        ret.append(app_commands.Choice(name=name, value=val))
                    case _:
                        pass

        return ret
    
    @app_commands.command(name="request")
    @app_commands.guild_only()
    @app_commands.autocomplete(query=query_autocomplete)
    async def request(self, interaction: discord.Interaction, query: str):
        if not await self._is_guild_whitelisted(interaction):
            return await interaction.response.send_message('This guild is not whitelisted for that command', ephemeral=True)
        overseerr_keys = await self.bot.get_shared_api_tokens("overseerr")
        if overseerr_keys.get("api_key") is None:
            return await interaction.response.send_message("Overseerr API key not set. Use `[p]set api` with service `overseerr` to set the `api_key` value", ephemeral=True)
        
        results = []
        match = re.match(r'^<id:(?P<id>\d+)>,<type:(?P<type>(?:movie|tv))>$', query)
        query = re.sub(r'[^a-zA-Z\d\s]', '', query.strip())
        if match:
            media_id = int(match.group('id'))
            media_type = match.group('type')
            item = await self.api.get_item(media_type, media_id)
            if item:
                results.append(item | {'mediaType': media_type})
        else:
            if unfiltered_results := await self.api.search(query):
                for r in unfiltered_results:
                    if r['mediaType'] in ['movie', 'tv']:
                        results.append(r)
        
        if not results:
            raise commands.UserFeedbackCheckFailure('There were no results for your query')
            #return await interaction.response.send_message("no results found for that query", ephemeral=True)
    
        user_id = await self.api.get_user_by_discord_id(str(interaction.user.id))

        await RequestView(cog=self).start(interaction, results=results, user=user_id)
    
    async def make_request(self, media_type, media_id, user_id=None):
        if await self.api.create_request(media_type, media_id, user_id=user_id):
            return True
        return False

    async def get_embed(
        self, ctx: commands.Context, result: dict
    ) -> discord.Embed:
        assert result['mediaType'] in ['movie','tv']
        title = result['title'] if 'title' in result else result['name']
        media_type = result['mediaType']
        overview = result['overview']
        release_date = result['releaseDate'] if 'releaseDate' in result else result['firstAirDate'] if 'firstAirDate' in result else 'N/A'
        og_title = result['originalTitle'] if 'originalTitle' in result else result['originalName'] if 'originalName' in result else 'N/A'
        media_id = result['id']

        poster_url = None
        if result['posterPath']:
            poster_url = f"https://media.themoviedb.org/t/p/original/{result['posterPath']}"

        embed = discord.Embed(
            title=title,
            color=await ctx.embed_color()
        )
        if poster_url:
            embed.set_thumbnail(url=poster_url)
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        embed.description = overview

        embed.add_field(name='Release Date', value=release_date)
        embed.add_field(name='Original Title',value=og_title)
        embed.add_field(name='Type', value=media_type)

        return embed

    
    @commands.group(name="ovset", autohelp=True)
    @commands.is_owner()
    async def ovset_group(self, ctx):
        pass

    @commands.group(name="overseerr", aliases=["ov", "over"])
    @commands.guild_only()
    async def overseerr_group(self, ctx):
        pass

    @ovset_group.group(name="whitelist")
    @commands.is_owner()
    async def whitelist_group(self, ctx):
        pass

    @whitelist_group.command(name="add")
    @commands.is_owner()
    async def _add_guild_to_whitelist(self, ctx, guild_id: str):
        guild_id = guild_id.strip()
        if not guild_id or not re.match(r'^\d+$', guild_id):
            raise commands.UserFeedbackCheckFailure('invalid guild id')
        wl = await self.config.guild_whitelist()
        wl.append(int(guild_id))
        wl = list(set(wl))
        await self.config.guild_whitelist.set(wl)
        return await ctx.send(f'added guild {guild_id} to whitelist')

    @whitelist_group.command(name="remove")
    @commands.is_owner()
    async def _remove_guild_from_whitelist(self, ctx, guild_id: str):
        guild_id = guild_id.strip()
        if not guild_id or not re.match(r'^(\d+|all)$', guild_id):
            raise commands.UserFeedbackCheckFailure('invalid guild id')
        if guild_id == 'all':
            await self.config.guild_whitelist.set([])
            return await ctx.send('cleared the whitelist')
        guild_id_int = int(guild_id)
        wl = await self.config.guild_whitelist()
        if guild_id_int in wl:
            wl.remove(guild_id_int)
            await self.config.guild_whitelist.set(wl)
            return await ctx.send('removed guild from whitelist')
        raise commands.UserFeedbackCheckFailure('guild was not whitelisted')

    @ovset_group.command(name="endpoint")
    @commands.is_owner()
    async def _set_endpoint(self, ctx, endpoint):
        endpoint = endpoint.strip()
        endpoint_regex = r"^(?P<protocol>https?):\/\/(?P<host>(?:[a-zA-Z\d.-]+|\[[a-fA-F\d:]+\])):?(?P<port>\d{1,5})?\/api\/(?P<version>v\d)$"
        if not endpoint or not re.match(endpoint_regex, endpoint):
            raise commands.UserFeedbackCheckFailure("invalid endpoint url")
        await self.config.endpoint.set(endpoint)
        self.api.endpoint = endpoint

    @ovset_group.command(name="showendpoint")
    @commands.is_owner()
    async def _show_endpoint(self, ctx):
        await ctx.send(self.api.endpoint if self.api.endpoint else "no endpoint configured")

    @overseerr_group.command(name="search", aliases=["se", "s"])
    @commands.guild_only()
    async def search(self, ctx, *args):
        if not await self._is_guild_whitelisted(ctx):
            return await ctx.send('This guild is not whitelisted for that command')
        query = ' '.join(map(str, args))
        query = re.sub(r'[^a-zA-Z\d\s]', '', query.strip())
        if not query:
            await ctx.send("no query")
            return

        overseerr_keys = await self.bot.get_shared_api_tokens("overseerr")
        if overseerr_keys.get("api_key") is None:
            return await ctx.send("Overseerr API key not set. Use `[p]set api` with service `overseerr` to set the `api_key` value")

        results = []
        unfiltered_results = await self.api.search(query)
        for r in unfiltered_results:
            if r['mediaType'] in ['movie', 'tv']:
                results.append(r)

        if not results:
            return await ctx.send("no results found for that query")

        await SearchView(cog=self).start(ctx, results=results)

    @overseerr_group.command(name="me")
    @commands.guild_only()
    async def whoami(self, ctx):
        if not await self._is_guild_whitelisted(ctx):
            return await ctx.send('gtfoh')
        user = await self.api.get_user_by_discord_id(str(ctx.author.id))
        return await ctx.send(str(user))
