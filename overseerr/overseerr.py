import discord
import asyncio
import datetime
import re

from redbot.core import commands, app_commands
from redbot.core import Config

from .api import Overseerr_API
from .view import RequestView

UNIQUE_ID = 0x6714473D

class Overseerr(commands.Cog):
    """Make requests to an overseerr endpoint"""

    def __init__(self, bot):
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        default_global = {
            "endpoint": None,
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
            self.api.set_api_key(api_tokens['api_key'])

    async def query_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> [app_commands.Choice[str]]:
        results = await self.api.search(current.strip())
        ret = []
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
        overseerr_keys = await self.bot.get_shared_api_tokens("overseerr")
        if overseerr_keys.get("api_key") is None:
            return await interaction.response.send_message("Overseerr API key not set. Use `[p]set api` with service `overseerr` to set the `api_key` value", ephemeral=True)
        
        results = []
        match = re.match(r'^<id:(?P<id>\d+)>,<type:(?P<type>(?:movie|tv))>$', query)
        if match:
            media_id = int(match.group('id'))
            media_type = match.group('type')
            item = await self.api.get_item(media_type, media_id)
            if item:
                results.append(item | {'mediaType': media_type})
        else:
            unfiltered_results = await self.api.search(query)
            for r in unfiltered_results:
                if r['mediaType'] in ['movie', 'tv']:
                    results.append(r)
        
        if not results:
            return await interaction.response.send_message("no results found for that query")
    
        user_id = await self.api.get_user_by_discord_id(str(interaction.user.id))

        await RequestView(cog=self).start(interaction, results=results, user=user_id)
    
    async def make_request(self, media_type, media_id, user_id=None):
        if await self.api.create_request(media_type, media_id, user_id=user_id):
            return True
        return False

    async def get_embed(
        self, ctx: commands.Context, result: {}
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

    
    @commands.group(name="requestset", autohelp=True)
    @commands.is_owner()
    async def requestset(self, ctx):
        pass

    @commands.group(name="overseerr", aliases=["ov", "over"])
    @commands.guild_only()
    async def overseerr(self, ctx):
        pass

    @requestset.command(name="endpoint")
    @commands.is_owner()
    async def _set_endpoint(self, ctx, endpoint):
        endpoint = endpoint.strip()
        endpoint_regex = r"^(?P<protocol>https?):\/\/(?P<host>(?:[a-zA-Z\d.-]+|\[[a-fA-F\d:]+\])):?(?P<port>\d{1,5})?\/api\/(?P<version>v\d)$"
        if endpoint and not re.match(endpoint_regex, endpoint):
            return await ctx.send("invalid endpoint url")
        await self.config.endpoint.set(endpoint)
        self.api.endpoint = endpoint

    @requestset.command(name="showendpoint")
    @commands.is_owner()
    async def _show_endpoint(self, ctx):
        await ctx.send(self.api.endpoint if self.api.endpoint else "no endpoint configured")
    
    @overseerr.command(name="search", aliases=["se", "s"])
    @commands.guild_only()
    async def search(self, ctx, query: str):
        data = await self.api.search(query)
        msg = ""
        if data:
            first = data[0]
            title = first['title']
            desc = first['overview']
            release_date = first['releaseDate']
            release_type = first['mediaType']
            score = first['voteAverage']
            msg += f"{title=}\n{desc=}\n{release_date=}\n{release_type=}\n{score=}"
        return await ctx.send(msg)

    @overseerr.command(name="me")
    @commands.guild_only()
    async def whoami(self, ctx):
        user = await self.api.get_user_by_discord_id(str(ctx.author.id))
        await ctx.send(str(user))